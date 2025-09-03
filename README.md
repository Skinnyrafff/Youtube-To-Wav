# YouTube a WAV

¡Una herramienta súper sencilla para bajar el audio de videos de YouTube y guardarlo como WAV!

## ¿Qué necesitas?

*   **Python 3:** Si no lo tienes, ¡a instalarlo!
*   **yt-dlp:** Un programita que hace la magia de bajar el audio. Lo instalas con este comando en tu terminal:
    ```
    pip install yt-dlp
    ```
*   **FFmpeg:** Esta es clave para convertir el audio.
    1.  Descárgalo desde [la página oficial de FFmpeg](https://ffmpeg.org/download.html).
    2.  Descomprímelo donde quieras.
    3.  **¡Importante!** Añade la carpeta `bin` de FFmpeg al PATH de tu sistema para que la terminal lo encuentre.

## ¿Cómo se usa?

### Con la interfaz gráfica (¡la forma fácil!)

1.  Ve a la carpeta del proyecto.
2.  Dale doble clic al archivo `start_gui.bat`.
3.  Se abrirá una ventana. Pega el link de YouTube, dale a "Descargar" y ¡listo!

### Desde la terminal (para los más pros)

Abre una terminal en la carpeta del proyecto y escribe esto (cambia "URL_AQUI" por el link del video):

```
python yt_to_wav.py "URL_AQUI"
```

## ¿Y los audios?

Todos los archivos `.wav` que bajes se guardarán en la carpeta `wav_output`.