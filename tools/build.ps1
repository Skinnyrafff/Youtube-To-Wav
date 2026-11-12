<#
  Compila LA CIFRA DOWNLOADER y arma el instalador.

  Uso (desde la raíz del repo):
      powershell -ExecutionPolicy Bypass -File tools\build.ps1
      powershell -ExecutionPolicy Bypass -File tools\build.ps1 -Version v1.2.0

  Resultado:
      dist\LaCifraDownloader\                     la app compilada (para probar)
      dist\installer\LaCifraDownloader-Setup-X.exe el instalador para compartir
#>
param(
    [string]$Version = "",
    [switch]$SkipInstaller
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # Invoke-WebRequest es mucho más rápido sin barra
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

# 1) Versión: el tag v1.2.3 se escribe en la_cifra/__init__.py
$init = "la_cifra\__init__.py"
if ($Version) {
    $v = $Version.TrimStart("v", "V")
    (Get-Content $init -Raw -Encoding utf8) -replace '__version__ = ".*"', "__version__ = `"$v`"" |
        Set-Content $init -Encoding utf8 -NoNewline
}
$v = ([regex]::Match((Get-Content $init -Raw), '__version__ = "(.*)"')).Groups[1].Value
Write-Host "==> Versión $v"

# 2) Herramientas que van dentro del instalador (se descargan una sola vez a vendor\bin)
$bin = "vendor\bin"
New-Item -ItemType Directory -Force $bin | Out-Null
$tmp = Join-Path ([IO.Path]::GetTempPath()) "lacifra-build"
New-Item -ItemType Directory -Force $tmp | Out-Null

if (-not (Test-Path "$bin\ffmpeg.exe")) {
    Write-Host "==> Descargando FFmpeg"
    Invoke-WebRequest "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile "$tmp\ffmpeg.zip"
    Expand-Archive "$tmp\ffmpeg.zip" "$tmp\ffmpeg" -Force
    Copy-Item (Get-ChildItem "$tmp\ffmpeg" -Recurse -Filter ffmpeg.exe | Select-Object -First 1).FullName "$bin\ffmpeg.exe"
}
if (-not (Test-Path "$bin\deno.exe")) {
    Write-Host "==> Descargando Deno"
    Invoke-WebRequest "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip" -OutFile "$tmp\deno.zip"
    Expand-Archive "$tmp\deno.zip" "$bin" -Force
}

# 3) PyInstaller: carpeta con el .exe (arranca rápido, sin descomprimir nada al abrir)
Write-Host "==> Compilando con PyInstaller"
python -m PyInstaller --noconfirm --clean --windowed `
    --name LaCifraDownloader `
    --icon assets\icon.ico `
    --add-data "assets\logo.png;assets" `
    --add-data "assets\icon.ico;assets" `
    --add-data "assets\icon.png;assets" `
    --add-binary "$bin\ffmpeg.exe;bin" `
    --add-binary "$bin\deno.exe;bin" `
    --collect-all customtkinter `
    --collect-all yt_dlp_ejs `
    la_cifra_downloader.pyw
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falló" }

if ($SkipInstaller) { Write-Host "==> Listo: dist\LaCifraDownloader\LaCifraDownloader.exe"; exit 0 }

# 4) Instalador con Inno Setup
$iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
foreach ($p in @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
                 "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe")) {
    if (-not $iscc -and (Test-Path $p)) { $iscc = $p }
}
if (-not $iscc) { throw "No se encontró Inno Setup 6 (ISCC.exe). Instálalo o usa -SkipInstaller." }
Write-Host "==> Armando instalador"
& $iscc /Q "/DAppVersion=$v" installer\la_cifra.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falló" }
Write-Host "==> Listo: dist\installer\LaCifraDownloader-Setup-$v.exe"
