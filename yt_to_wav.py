import argparse
from pathlib import Path
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

# --- Dependencias ---
# Este script requiere la siguiente biblioteca de Python:
# - yt-dlp: pip install yt-dlp
#
# También requiere FFmpeg. El script buscará automáticamente una carpeta llamada
# 'ffmpeg-8.0-essentials_build' en el mismo directorio. Si no la encuentra,
# intentará usar una instalación global de FFmpeg (si existe en el PATH).
# --------------------

def on_progress(d):
    """Muestra el progreso de la descarga."""
    if d.get('status') == 'downloading':
        p = d.get('_percent_str', '').strip()
        spd = d.get('_speed_str', '').strip()
        eta = d.get('_eta_str', '').strip()
        print(f"Descargando: {p} | Velocidad: {spd} | ETA: {eta}", end='\r')
    elif d.get('status') == 'finished':
        print("\nDescarga completa, convirtiendo a WAV...")

def download_to_wav(url: str, out_dir: str = "salida", sample_rate: str = "44100", channels: str = "2"):
    """
    Descarga el audio de una URL de YouTube y lo convierte a formato WAV.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # --- Lógica para hacer FFmpeg portable ---
    script_dir = Path(__file__).parent
    ffmpeg_dir = script_dir / "ffmpeg-8.0-essentials_build" / "bin"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(Path(out_dir) / "% (title)s.%(ext)s"),
        "noplaylist": True,
        "progress_hooks": [on_progress],
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "0",
        }],
        "postprocessor_args": ["-ar", sample_rate, "-ac", channels],
        "quiet": True, # Desactiva los logs de yt-dlp para que no interfieran con nuestro hook
    }

    # Si la carpeta local de ffmpeg existe, la usamos. Si no, yt-dlp buscará en el PATH.
    if ffmpeg_dir.exists():
        ydl_opts["ffmpeg_location"] = str(ffmpeg_dir)
    # -----------------------------------------

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            # Obtener el nombre del archivo final para mostrarlo
            base_filename = ydl.prepare_filename(info_dict).rsplit('.', 1)[0]
            output_filename = f"{base_filename}.wav"
            print(f"¡Éxito! Audio guardado en: {output_filename}")

    except DownloadError as e:
        print(f"\nError: No se pudo descargar o procesar el video.")
        # Añadimos una comprobación específica para el error de ffmpeg
        if "ffmpeg not found" in str(e):
            print("Detalle: FFmpeg no se encontró en la ruta del sistema ni en la carpeta local del script.")
            print("Asegúrate de que ffmpeg.exe esté en la carpeta 'ffmpeg-8.0-essentials_build/bin' o instalado globalmente.")
        else:
            print(f"Detalle: {e}")
    except Exception as e:
        print(f"\nOcurrió un error inesperado: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Descarga el audio de un video de YouTube y lo convierte a WAV.",
        epilog="Ejemplo: python yt_to_wav.py \"https://www.youtube.com/watch?v=dQw4w9WgXcQ\" -o mi_audio --rate 48000"
    )
    parser.add_argument(
        "url",
        help="La URL del video de YouTube."
    )
    parser.add_argument(
        "-o", "--output",
        default="wav_output",
        help="Directorio donde se guardará el archivo WAV. (default: wav_output)"
    )
    parser.add_argument(
        "--rate",
        default="44100",
        help="Tasa de muestreo del archivo WAV (ej. 44100, 48000). (default: 44100)"
    )
    parser.add_argument(
        "--channels",
        default="2",
        help="Número de canales de audio (1 para mono, 2 para estéreo). (default: 2)"
    )

    args = parser.parse_args()

    download_to_wav(args.url, args.output, args.rate, args.channels)

if __name__ == "__main__":
    main()
