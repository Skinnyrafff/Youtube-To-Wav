"""Descarga y conversión. No depende de la interfaz: comunica todo con eventos.

Eventos que emite (tuplas):
    ("log", texto)                       ("status", texto)
    ("title", título)                    ("progress", "download"|"convert", fracción|None, detalle)
    ("done", ruta_final)                 ("cancelled",)
    ("error", mensaje)
"""
import io
import json
import re
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadCancelled, DownloadError

from .paths import find_ffmpeg, js_runtimes

FORMATS = ("wav", "mp3")
WAV_BITS = {"16 bits": "pcm_s16le", "24 bits": "pcm_s24le", "32 bits (float)": "pcm_f32le"}
MP3_BITRATES = {"128 kbps": "128", "192 kbps": "192", "256 kbps": "256", "320 kbps": "320"}
DEFAULT_QUALITY = {"wav": "16 bits", "mp3": "320 kbps"}

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

Emit = Callable[[tuple], None]


class _Logger:
    """Pasa los mensajes de yt-dlp como eventos de log."""

    def __init__(self, emit: Emit | None = None):
        self.emit = emit

    def _log(self, msg):
        if self.emit:
            self.emit(("log", msg))

    def debug(self, msg):
        self._log(msg[8:] if msg.startswith("[debug] ") else msg)

    def info(self, msg):
        self._log(msg)

    def warning(self, msg):
        self._log(f"AVISO: {msg}")

    def error(self, msg):
        self._log(msg)


def base_ydl_options(emit: Emit | None = None) -> dict:
    opts = {
        "noplaylist": True,
        "noprogress": True,
        "logger": _Logger(emit),
        "js_runtimes": js_runtimes(),
    }
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        opts["ffmpeg_location"] = str(ffmpeg.parent)
    return opts


# --- Vista previa (portada + título) ---

YT_ID_RE = re.compile(r"(?:youtube\.com/.*[?&]v=|youtu\.be/|youtube\.com/(?:shorts|embed|live)/)([A-Za-z0-9_-]{11})")


def _http_get(url: str, timeout: float = 8) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_preview(url: str):
    """Devuelve (título, canal, imagen PIL o None). Rápido para YouTube; yt-dlp para el resto."""
    from PIL import Image

    match = YT_ID_RE.search(url)
    if match:
        vid = match.group(1)
        image = Image.open(io.BytesIO(_http_get(f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg")))
        title = author = None
        try:
            oembed = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(
                f"https://www.youtube.com/watch?v={vid}", safe="")
            data = json.loads(_http_get(oembed))
            title, author = data.get("title"), data.get("author_name")
        except Exception:  # noqa: BLE001  (videos con inserción deshabilitada no tienen oEmbed)
            pass
        return title, author, image

    with YoutubeDL(base_ydl_options()) as ydl:
        info = ydl.extract_info(url, download=False)
    image = None
    if info.get("thumbnail"):
        try:
            image = Image.open(io.BytesIO(_http_get(info["thumbnail"])))
        except Exception:  # noqa: BLE001
            pass
    return info.get("title"), info.get("uploader") or info.get("channel"), image


# --- Descarga + conversión ---

class Downloader:
    def __init__(self, emit: Emit):
        self.emit = emit
        self.cancel_requested = False

    def log(self, msg):
        self.emit(("log", msg))

    def _progress_hook(self, d):
        if self.cancel_requested:
            raise DownloadCancelled()
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            done = d.get("downloaded_bytes", 0)
            frac = min(done / total, 1.0) if total else None
            speed = (d.get("_speed_str") or "").strip()
            eta = (d.get("_eta_str") or "").strip()
            detail = "  ·  ".join(x for x in (speed, f"quedan {eta}" if eta else "") if x)
            self.emit(("progress", "download", frac, detail))
        elif d.get("status") == "finished":
            self.emit(("progress", "download", 1.0, ""))

    def _convert(self, ffmpeg: Path, src: Path, dst: Path, fmt: str, quality: str, duration):
        """Convierte con FFmpeg informando el progreso real."""
        if fmt == "wav":
            codec = ["-acodec", WAV_BITS[quality]]
        else:
            codec = ["-acodec", "libmp3lame", "-b:a", MP3_BITRATES[quality] + "k"]
        tmp = dst.with_name(dst.stem + ".part" + dst.suffix)
        cmd = [str(ffmpeg), "-y", "-hide_banner", "-nostdin", "-i", str(src), "-vn", "-map_metadata", "0",
               *codec, "-progress", "pipe:1", "-nostats", str(tmp)]
        self.log("FFmpeg: " + " ".join(f'"{c}"' if " " in c else c for c in cmd))

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
        err_lines: list[str] = []
        threading.Thread(target=lambda: err_lines.extend(proc.stderr), daemon=True).start()

        self.emit(("progress", "convert", 0.0 if duration else None, ""))
        for line in proc.stdout:
            if self.cancel_requested:
                proc.kill()
                proc.wait()
                tmp.unlink(missing_ok=True)
                raise DownloadCancelled()
            key, _, value = line.strip().partition("=")
            if key == "out_time_us" and duration and value.isdigit():
                self.emit(("progress", "convert", min(int(value) / 1e6 / duration, 1.0), ""))
        proc.wait()

        if proc.returncode != 0:
            tmp.unlink(missing_ok=True)
            for err in err_lines[-15:]:
                self.log(err.rstrip())
            raise RuntimeError(f"FFmpeg falló (código {proc.returncode}). Revisa los logs.")
        tmp.replace(dst)
        self.emit(("progress", "convert", 1.0, ""))

    def run(self, url: str, out_dir: Path, fmt: str, quality: str):
        src = None
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            ffmpeg = find_ffmpeg()
            self.log(f"URL: {url}")
            self.log(f"Formato: {fmt.upper()} · {quality}")
            self.log(f"Destino: {out_dir}")
            self.log(f"FFmpeg: {ffmpeg or 'NO ENCONTRADO'}")
            self.log(f"JavaScript: {js_runtimes()}")
            if not ffmpeg:
                self.emit(("error", "No se encontró FFmpeg. Reinstala el programa."))
                return

            opts = base_ydl_options(self.emit) | {
                "format": "bestaudio/best",
                "outtmpl": str(out_dir / "%(title)s.%(ext)s"),
                "windowsfilenames": True,
                "progress_hooks": [self._progress_hook],
            }

            self.emit(("status", "Buscando el video..."))
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                self.emit(("title", info.get("title") or "Sin título"))
                if self.cancel_requested:
                    raise DownloadCancelled()
                info = ydl.process_ie_result(info, download=True)

            src = Path((info.get("requested_downloads") or [{}])[0].get("filepath") or "")
            if not src.is_file():
                raise RuntimeError("No se encontró el archivo descargado.")
            dst = src.with_suffix("." + fmt)
            self._convert(ffmpeg, src, dst, fmt, quality, info.get("duration"))
            if src != dst:
                src.unlink(missing_ok=True)

            self.log(f"Archivo final: {dst}")
            self.emit(("done", str(dst)))

        except DownloadCancelled:
            self.log("Cancelado por el usuario.")
            self.emit(("cancelled",))
        except DownloadError as e:
            msg = str(e)
            if "is not a valid URL" in msg or "Unsupported URL" in msg:
                msg = "El enlace no parece ser un video válido."
            elif "Video unavailable" in msg:
                msg = "El video no está disponible."
            elif "Private video" in msg:
                msg = "El video es privado."
            else:
                msg = msg.replace("ERROR: ", "")
            self.emit(("error", msg))
        except Exception as e:  # noqa: BLE001
            self.log(f"Error: {e!r}")
            self.emit(("error", str(e)))
        finally:
            # Si se canceló o falló después de descargar, borramos el archivo original
            if src and src.is_file() and src.suffix.lower() != "." + fmt:
                try:
                    src.unlink()
                except OSError:
                    pass
