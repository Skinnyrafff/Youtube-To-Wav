"""Detalles de integración con Windows (Explorador, barra de título, ícono en la barra de tareas)."""
import base64
import os
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"


def set_app_id(app_id: str):
    """Para que la barra de tareas muestre el ícono de la app y no el de Python."""
    if IS_WINDOWS:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)


def _colorref(hex_color: str) -> int:
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    return r | (g << 8) | (b << 16)


def paint_title_bar(window, background: str, text: str):
    """Windows 11: barra de título y borde del mismo color que la app.
    Windows 10 ignora los colores y deja la barra oscura estándar."""
    if not IS_WINDOWS:
        return
    try:
        import ctypes
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        dwm = ctypes.windll.dwmapi
        for attr, value in ((20, 1),                       # modo oscuro
                            (34, _colorref(background)),   # borde
                            (35, _colorref(background)),   # barra de título
                            (36, _colorref(text))):        # texto del título
            v = ctypes.c_int(value)
            dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), 4)
    except Exception:  # noqa: BLE001
        pass


_REVEAL_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
$dir = {dir}.TrimEnd('\'); $file = {file}; $prev = {prev}.TrimEnd('\')
$sh = New-Object -ComObject Shell.Application
$win = $null
foreach ($w in @($sh.Windows())) {
  $p = $null; try { $p = $w.Document.Folder.Self.Path.TrimEnd('\') } catch {}
  if ($p -and ($p -eq $dir -or ($prev -and $p -eq $prev))) { $win = $w; break }
}
if (-not $win) {
  if ($file) { Start-Process explorer.exe -ArgumentList "/select,`"$file`"" }
  else { Start-Process explorer.exe -ArgumentList "`"$dir`"" }
  exit
}
if ($win.Document.Folder.Self.Path.TrimEnd('\') -ne $dir) {
  $win.Navigate2($dir)
  for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 100
    if (-not $win.Busy -and $win.Document.Folder.Self.Path.TrimEnd('\') -eq $dir) { break }
  }
}
if ($file) {
  $name = Split-Path $file -Leaf
  for ($i = 0; $i -lt 20; $i++) { $item = $win.Document.Folder.ParseName($name); if ($item) { break }; Start-Sleep -Milliseconds 100 }
  if ($item) { $win.Document.SelectItem($item, 29) }
}
Add-Type -Name W -Namespace U -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c); [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);'
$h = [IntPtr]$win.HWND
if ([U.W]::IsIconic($h)) { [U.W]::ShowWindow($h, 9) | Out-Null }
[U.W]::SetForegroundWindow($h) | Out-Null
"""


def reveal_in_explorer(file: str | None, folder: Path, previous_folder: Path | None = None):
    """Abre la carpeta con el archivo seleccionado. Si ya hay una ventana del Explorador
    en esa carpeta (o en la carpeta anterior) la reutiliza en vez de abrir otra."""
    if not IS_WINDOWS:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(folder)])
        return

    def literal(s) -> str:  # cadena literal de PowerShell
        return "'" + str(s or "").replace("'", "''") + "'"

    script = (_REVEAL_SCRIPT
              .replace("{dir}", literal(os.path.normpath(folder)))
              .replace("{file}", literal(file and os.path.normpath(file)))
              .replace("{prev}", literal(previous_folder and os.path.normpath(previous_folder))))
    import ctypes
    ctypes.windll.user32.AllowSetForegroundWindow(-1)  # deja que el Explorador pase al frente
    encoded = base64.b64encode(script.encode("utf-16-le")).decode()
    subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                      "-EncodedCommand", encoded], creationflags=subprocess.CREATE_NO_WINDOW)
