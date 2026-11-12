"""Genera los PNG e ICO de la app a partir de los SVG en assets/svg.

Uso: python tools/generar_assets.py
"""
from pathlib import Path

from render_svg import render

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "assets" / "svg"
OUT = ROOT / "assets"

# Logo para fondo negro: letras crema con sombra marrón (paleta del ícono)
LOGO_SOBRE_NEGRO = {"#1A1714": "#EFE7D8", "#D3C4AA": "#6B5A45"}


def main():
    # Logo del encabezado (alto 96 px = 48 px en pantalla al 200 %)
    logo = render(SVG / "la-cifra.svg", 352, recolor=LOGO_SOBRE_NEGRO)
    logo.save(OUT / "logo.png")

    # Ícono: ventana, barra de tareas y ejecutable.
    # Cada tamaño se dibuja directo desde el SVG (no achicando uno grande) para que se vea nítido.
    sizes = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
    frames = {s: render(SVG / "cifra-icono.svg", s, ss=max(4, 1024 // s)) for s in sizes}
    frames[256].save(OUT / "icon.png")
    frames[256].save(OUT / "icon.ico", format="ICO", sizes=[(s, s) for s in sizes],
                     append_images=[frames[s] for s in sizes if s != 256])
    print("Listo:", ", ".join(p.name for p in OUT.glob("*.*")))


if __name__ == "__main__":
    main()
