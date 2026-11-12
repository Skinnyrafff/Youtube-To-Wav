"""Rutas de la app, herramientas externas (FFmpeg, Deno) y configuración del usuario."""
import json
import os
import shutil
import sys
from pathlib import Path

from . import APP_NAME

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IS_FROZEN = getattr(sys, "frozen", False)
EXE_SUFFIX = ".exe" if sys.platform == "win32" else ""


def bundle_dir() -> Path:
    """Donde están los archivos empaquetados (assets/, bin/)."""
    return Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))


def asset(name: str) -> Path:
    return bundle_dir() / "assets" / name


def _find_tool(name: str) -> Path | None:
    """Busca una herramienta: la incluida en el instalador, vendor/bin (desarrollo) o el PATH."""
    for folder in (bundle_dir() / "bin", PROJECT_ROOT / "vendor" / "bin"):
        candidate = folder / f"{name}{EXE_SUFFIX}"
        if candidate.is_file():
            return candidate
    found = shutil.which(name)
    return Path(found) if found else None


def find_ffmpeg() -> Path | None:
    return _find_tool("ffmpeg")


def js_runtimes() -> dict:
    """Motor de JavaScript que yt-dlp necesita para YouTube (Deno incluido, o el del sistema)."""
    deno = _find_tool("deno")
    if deno:
        return {"deno": {"path": str(deno)}}
    return {"deno": {}, "node": {}}


# --- Carpetas del usuario ---

KNOWN_FOLDERS = [
    ("Descargas", "{374DE290-123F-4565-9164-39C4925E467B}", "Downloads"),
    ("Música", "{4BD8D571-6D19-48D3-BE97-422220080E43}", "Music"),
    ("Escritorio", "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}", "Desktop"),
    ("Documentos", "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}", "Documents"),
    ("Videos", "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}", "Videos"),
]


def known_folder(guid: str, fallback: str) -> Path:
    """Ruta real de una carpeta del usuario (respeta OneDrive o si se movió a otro disco)."""
    if sys.platform == "win32":
        try:
            import ctypes
            import uuid

            class GUID(ctypes.Structure):
                _fields_ = [("data", ctypes.c_ubyte * 16)]

            g = GUID()
            ctypes.memmove(g.data, uuid.UUID(guid).bytes_le, 16)
            out = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(out)) == 0:
                path = Path(out.value)
                ctypes.windll.ole32.CoTaskMemFree(out)
                return path
        except Exception:  # noqa: BLE001
            pass
    return Path.home() / fallback


def user_folders() -> list[tuple[str, Path]]:
    return [(name, p) for name, guid, fb in KNOWN_FOLDERS if (p := known_folder(guid, fb)).is_dir()]


# --- Configuración (recuerda la carpeta de destino) ---

CONFIG_FILE = Path(os.getenv("APPDATA") or Path.home()) / APP_NAME / "config.json"


def load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def save_config(data: dict):
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
