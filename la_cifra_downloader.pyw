"""Abre LA CIFRA DOWNLOADER (doble clic: .pyw se abre sin consola).

Diagnóstico: LaCifraDownloader.exe --selftest informe.txt
  descarga un video corto a una carpeta temporal y guarda en informe.txt qué encontró y qué pasó.
"""
import sys


def selftest(report_path: str):
    import tempfile
    from pathlib import Path

    from la_cifra import __version__
    from la_cifra.core import Downloader
    from la_cifra.paths import bundle_dir, find_ffmpeg, js_runtimes

    lines = [f"version={__version__}", f"bundle={bundle_dir()}",
             f"ffmpeg={find_ffmpeg()}", f"js={js_runtimes()}"]
    events = []
    with tempfile.TemporaryDirectory() as tmp:
        Downloader(events.append).run("https://www.youtube.com/watch?v=jNQXAC9IVRw", Path(tmp), "wav", "16 bits")
    lines += [repr(e) for e in events if e[0] != "progress"]
    Path(report_path).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--selftest":
        selftest(sys.argv[2])
    else:
        from la_cifra.gui import main
        main()
