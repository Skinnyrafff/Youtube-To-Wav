<p align="center"><img src="assets/icon.png" width="96" alt="LA CIFRA"></p>

# LA CIFRA DOWNLOADER

Descarga el audio de videos de YouTube en **WAV** (16, 24 o 32 bits) o **MP3** (128 a 320 kbps).

## Instalar

1. Ve a [**Releases**](https://github.com/Skinnyrafff/Youtube-To-Wav/releases/latest) y descarga `LaCifraDownloader-Setup-X.Y.Z.exe`.
2. Ábrelo y sigue los pasos. No necesita permisos de administrador ni instalar nada más.
3. Si Windows muestra "Windows protegió su PC", haz clic en **Más información → Ejecutar de todas formas**. Aparece porque el instalador no está firmado digitalmente.

Para actualizar, usa el botón **Buscar actualización** al pie de la app: descarga la versión nueva, la instala y vuelve a abrirse sola.

## Cómo se usa

1. Pega el enlace del video (aparece la portada y el título).
2. Elige el formato y la calidad.
3. Elige la carpeta de destino.
4. Presiona **Descargar**. Al terminar, se abre la carpeta con el archivo seleccionado.

Si algo falla, **Ver logs** muestra el detalle; el botón **Copiar** sirve para compartirlo.

---

## Para desarrolladores

### Ejecutar desde el código

Requiere Python 3.11+ y FFmpeg (en el `PATH` o en `vendor/bin`).

```
pip install -r requirements.txt
python la_cifra_downloader.pyw
```

En Windows también puedes abrir `abrir.bat` (sin consola).

Versión de terminal:

```
python yt_to_wav.py "URL" -f mp3 -q "320 kbps" -o "C:\carpeta"
```

### Estructura

```
la_cifra/
  core.py       descarga (yt-dlp) y conversión (FFmpeg) con progreso
  gui.py        interfaz (CustomTkinter)
  updater.py    actualizaciones desde GitHub Releases
  paths.py      rutas, FFmpeg/Deno incluidos, carpetas del usuario, configuración
  winutil.py    integración con Windows (Explorador, barra de título)
assets/         ícono y logo (generados desde assets/svg con tools/generar_assets.py)
installer/      script de Inno Setup
tools/build.ps1 compila la app y el instalador
la_cifra_downloader.pyw   punto de entrada de la app
yt_to_wav.py              versión de terminal
```

### Compilar el instalador

Requiere [Inno Setup 6](https://jrsoftware.org/isdl.php).

```
pip install -r requirements-build.txt
powershell -ExecutionPolicy Bypass -File tools\build.ps1
```

El script descarga FFmpeg y Deno a `vendor/bin` la primera vez. El resultado queda en `dist\installer\`.

### Publicar una versión

```
git tag v1.1.0
git push origin v1.1.0
```

GitHub Actions (`.github/workflows/release.yml`) compila el instalador y lo publica como Release. Las apps instaladas lo detectan al abrirse.

Cuando YouTube cambia algo y las descargas dejan de funcionar, normalmente basta con publicar una versión nueva: el workflow instala la última versión de yt-dlp.
