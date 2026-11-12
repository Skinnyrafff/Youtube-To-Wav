"""Actualizaciones desde los Releases de GitHub.

Cada Release publicado por el workflow incluye el instalador LaCifraDownloader-Setup-X.Y.Z.exe.
La app lo descarga, lo ejecuta en modo silencioso y se cierra; el instalador reemplaza los
archivos y vuelve a abrir la app.
"""
import json
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import EXE_NAME, GITHUB_REPO, __version__
from .paths import IS_FROZEN

LATEST_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"


@dataclass
class Release:
    version: str
    notes: str
    page_url: str
    installer_url: str | None
    installer_name: str | None
    size: int


def parse_version(v: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", v)[:3]) or (0,)


def is_newer(remote: str, local: str = __version__) -> bool:
    return parse_version(remote) > parse_version(local)


def latest_release(timeout: float = 10) -> Release | None:
    """Último Release publicado, o None si todavía no hay ninguno."""
    req = urllib.request.Request(LATEST_API, headers={
        "Accept": "application/vnd.github+json", "User-Agent": f"{EXE_NAME}/{__version__}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    installer = next((a for a in data.get("assets", [])
                      if a["name"].lower().endswith(".exe") and "setup" in a["name"].lower()), None)
    return Release(
        version=data.get("tag_name", "").lstrip("vV"),
        notes=(data.get("body") or "").strip(),
        page_url=data.get("html_url") or RELEASES_PAGE,
        installer_url=installer and installer["browser_download_url"],
        installer_name=installer and installer["name"],
        size=installer["size"] if installer else 0,
    )


def can_self_update() -> bool:
    """Solo la versión instalada se actualiza sola (desde el código se usa git pull)."""
    return IS_FROZEN and sys.platform == "win32"


def download_installer(release: Release, progress: Callable[[float], None],
                       cancelled: Callable[[], bool] = lambda: False) -> Path:
    dest = Path(tempfile.gettempdir()) / (release.installer_name or f"{EXE_NAME}-Setup.exe")
    tmp = dest.with_suffix(".part")
    req = urllib.request.Request(release.installer_url, headers={"User-Agent": f"{EXE_NAME}/{__version__}"})
    with urllib.request.urlopen(req, timeout=30) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or release.size or 0)
        done = 0
        while chunk := r.read(256 * 1024):
            if cancelled():
                raise InterruptedError("Actualización cancelada.")
            f.write(chunk)
            done += len(chunk)
            if total:
                progress(done / total)
    tmp.replace(dest)
    return dest


def run_installer(installer: Path):
    """Lanza el instalador en modo silencioso (muestra solo una barra de progreso).
    La app se cierra justo después; el instalador la vuelve a abrir al terminar
    (ver la sección [Run] de installer/la_cifra.iss)."""
    subprocess.Popen([str(installer), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
                     close_fds=True)
