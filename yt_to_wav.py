"""Versión de terminal de LA CIFRA DOWNLOADER.

Ejemplos:
    python yt_to_wav.py "https://www.youtube.com/watch?v=..."
    python yt_to_wav.py "URL" -f mp3 -q "320 kbps" -o "C:\\Users\\yo\\Music"
"""
import argparse
import sys
from pathlib import Path

from la_cifra.core import DEFAULT_QUALITY, FORMATS, MP3_BITRATES, WAV_BITS, Downloader
from la_cifra.paths import known_folder


def main():
    downloads = known_folder("{374DE290-123F-4565-9164-39C4925E467B}", "Downloads")
    parser = argparse.ArgumentParser(description="Descarga el audio de un video de YouTube en WAV o MP3.")
    parser.add_argument("url", help="Enlace del video.")
    parser.add_argument("-f", "--formato", choices=FORMATS, default="wav", help="wav (por defecto) o mp3.")
    parser.add_argument("-q", "--calidad",
                        help=f"WAV: {', '.join(WAV_BITS)}. MP3: {', '.join(MP3_BITRATES)}. "
                             "Por defecto 16 bits / 320 kbps.")
    parser.add_argument("-o", "--salida", type=Path, default=downloads,
                        help=f"Carpeta de destino (por defecto {downloads}).")
    parser.add_argument("-v", "--verbose", action="store_true", help="Muestra todos los mensajes de yt-dlp.")
    args = parser.parse_args()

    options = WAV_BITS if args.formato == "wav" else MP3_BITRATES
    calidad = args.calidad or DEFAULT_QUALITY[args.formato]
    if calidad not in options:
        parser.error(f"Calidad inválida para {args.formato.upper()}. Opciones: {', '.join(options)}")

    result = {"ok": False}
    finished_phases = set()

    def emit(ev):
        kind = ev[0]
        if kind == "log" and args.verbose:
            print(ev[1])
        elif kind == "status":
            print(ev[1])
        elif kind == "title":
            print(f"Video: {ev[1]}")
        elif kind == "progress" and ev[2] is not None and ev[1] not in finished_phases:
            label = "Descargando" if ev[1] == "download" else "Convirtiendo"
            print(f"\r{label}: {ev[2] * 100:5.1f}%  {ev[3]}".ljust(70), end="", flush=True)
            if ev[2] >= 1:
                finished_phases.add(ev[1])
                print()
        elif kind == "done":
            print(f"Listo: {ev[1]}")
            result["ok"] = True
        elif kind == "cancelled":
            print("\nCancelado.")
        elif kind == "error":
            print(f"\nError: {ev[1]}", file=sys.stderr)

    downloader = Downloader(emit)
    try:
        downloader.run(args.url, args.salida, args.formato, calidad)
    except KeyboardInterrupt:
        downloader.cancel_requested = True
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
