"""Renderiza SVGs simples (circle + path con M/L/Z) a PNG con Pillow.
Uso: python render_svg.py entrada.svg salida.png ancho_px [fondo_hex]
"""
import re
import sys

from PIL import Image, ImageChops, ImageDraw

SS = 4  # supersampling


def parse(svg_text):
    vb = [float(x) for x in re.search(r'viewBox="([^"]+)"', svg_text).group(1).split()]
    shapes = []
    for m in re.finditer(r"<(circle|path)\b([^>]*)/?>", svg_text):
        tag, attrs = m.group(1), m.group(2)
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', attrs))
        shapes.append((tag, a))
    return vb, shapes


def subpaths(d):
    polys, cur = [], []
    for cmd, args in re.findall(r"([MLZmlz])([^MLZmlz]*)", d):
        nums = [float(n) for n in re.findall(r"-?\d*\.?\d+(?:e-?\d+)?", args)]
        pts = list(zip(nums[0::2], nums[1::2]))
        if cmd == "M":
            if len(cur) > 2:
                polys.append(cur)
            cur = pts
        elif cmd == "L":
            cur += pts
        elif cmd in "Zz":
            if len(cur) > 2:
                polys.append(cur)
            cur = []
    if len(cur) > 2:
        polys.append(cur)
    return polys


def render(svg_path, width, background=None, recolor=None, ss=SS):
    """recolor: dict {"#color_original": "#color_nuevo"} para variantes (ej. logo claro)."""
    vb, shapes = parse(open(svg_path, encoding="utf-8").read())
    recolor = {k.upper(): v for k, v in (recolor or {}).items()}
    vx, vy, vw, vh = vb
    W = width * ss
    H = round(width * vh / vw) * ss
    sx, sy = W / vw, H / vh
    bg = (0, 0, 0, 0) if background is None else Image.new("RGB", (1, 1), background).getpixel((0, 0)) + (255,)
    canvas = Image.new("RGBA", (W, H), bg)

    for tag, a in shapes:
        fill = a.get("fill", "#000000")
        fill = recolor.get(fill.upper(), fill)
        mask = Image.new("L", (W, H), 0)
        if tag == "circle":
            cx, cy, r = (float(a[k]) for k in ("cx", "cy", "r"))
            ImageDraw.Draw(mask).ellipse(
                [(cx - r - vx) * sx, (cy - r - vy) * sy, (cx + r - vx) * sx, (cy + r - vy) * sy], fill=255)
        else:
            # Regla par-impar: cada subtrazo invierte el área (los huecos de las letras se recortan)
            for poly in subpaths(a["d"]):
                layer = Image.new("L", (W, H), 0)
                ImageDraw.Draw(layer).polygon([((x - vx) * sx, (y - vy) * sy) for x, y in poly], fill=255)
                mask = ImageChops.logical_xor(mask.convert("1"), layer.convert("1")).convert("L")
        color = Image.new("RGBA", (W, H), fill)
        canvas = Image.composite(color, canvas, mask)

    return canvas.resize((W // ss, H // ss), Image.LANCZOS)


if __name__ == "__main__":
    src, dst, w = sys.argv[1], sys.argv[2], int(sys.argv[3])
    bg = sys.argv[4] if len(sys.argv) > 4 else None
    render(src, w, bg).save(dst)
