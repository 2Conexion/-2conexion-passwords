#!/usr/bin/env python3
"""Genera las imágenes de marca en branding/images a partir de icono-origen.png y marca.env.

Para usar el logo oficial: reemplaza icono-origen.png (cuadrado, fondo transparente,
emblema sin texto, recortado al ras) y vuelve a ejecutar. Cualquier archivo de branding/images
se puede sustituir a mano por arte final; construir-web-vault.py copia lo que haya.
"""
import base64
import io
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parent
OUT = BASE / "images"
FONT_STACK = "Lato, 'Helvetica Neue', Helvetica, Arial, sans-serif"


def leer_marca():
    marca = {}
    for linea in (BASE / "marca.env").read_text(encoding="utf-8").splitlines():
        if "=" in linea and not linea.lstrip().startswith("#"):
            k, v = linea.split("=", 1)
            marca[k.strip()] = v.strip().strip('"')
    return marca


def placa_redondeada(lado, color):
    """Cuadro con esquinas redondeadas (dibujado a 4x y reducido para suavizar bordes)."""
    g = lado * 4
    r = g // 5
    mascara = Image.new("L", (g, g), 0)
    d = ImageDraw.Draw(mascara)
    d.rectangle([r, 0, g - r - 1, g - 1], fill=255)
    d.rectangle([0, r, g - 1, g - r - 1], fill=255)
    for x, y in ((0, 0), (g - 2 * r - 1, 0), (0, g - 2 * r - 1), (g - 2 * r - 1, g - 2 * r - 1)):
        d.ellipse([x, y, x + 2 * r, y + 2 * r], fill=255)
    placa = Image.new("RGBA", (lado, lado), color)
    placa.putalpha(mascara.resize((lado, lado), Image.LANCZOS))
    return placa


def emblema(ancho):
    """Emblema con su proporción original, al ancho pedido."""
    origen = Image.open(BASE / "icono-origen.png").convert("RGBA")
    return origen.resize((ancho, max(1, round(ancho * origen.height / origen.width))), Image.LANCZOS)


def icono(lado, fondo=None, margen=0.0):
    """Ícono cuadrado con el emblema centrado; con `fondo` va sobre una placa redondeada."""
    lienzo = placa_redondeada(lado, fondo) if fondo else Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    marca = emblema(max(1, round(lado * (1 - 2 * margen))))
    lienzo.alpha_composite(marca, ((lado - marca.width) // 2, (lado - marca.height) // 2))
    return lienzo


def data_uri(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def logo_svg(m, vb_ancho, vb_alto, relleno_1, relleno_2, clase=None):
    """Logotipo horizontal en SVG. Con `clase` el color del texto lo pone el tema de la bóveda."""
    e = vb_alto / 60
    marca = emblema(360)
    alto = 46 * e
    ancho = alto * marca.width / marca.height
    x_texto = ancho + 12 * e
    attr_1 = f'class="{clase}"' if clase else f'fill="{relleno_1}"'
    attr_2 = f'class="{clase}" opacity=".7"' if clase else f'fill="{relleno_2}"'
    return (
        f'<svg version="1.1" viewBox="0 0 {vb_ancho} {vb_alto}" xmlns="http://www.w3.org/2000/svg">'
        f'<title>{m["MARCA"]}</title>'
        f'<image x="0" y="{7*e:g}" width="{ancho:g}" height="{alto:g}" href="{data_uri(marca)}"/>'
        f'<text x="{x_texto:g}" y="{30*e:g}" font-family="{FONT_STACK}" font-size="{21*e:g}" '
        f'font-weight="400" letter-spacing="{2.2*e:g}" {attr_1}>{m["MARCA_LINEA1"]}</text>'
        f'<text x="{x_texto:g}" y="{50*e:g}" font-family="{FONT_STACK}" font-size="{15*e:g}" '
        f'font-weight="400" letter-spacing="{1.2*e:g}" {attr_2}>{m["MARCA_LINEA2"]}</text>'
        '</svg>'
    )


def icono_svg(m):
    return (
        '<svg version="1.1" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg">'
        f'<title>{m["MARCA"]}</title>'
        f'<image x="2" y="2" width="56" height="56" href="{data_uri(icono(224))}"/>'
        '</svg>'
    )


def main():
    m = leer_marca()
    OUT.mkdir(exist_ok=True)
    (OUT / "icons").mkdir(exist_ok=True)

    # Íconos de pestaña y de pantalla de inicio
    icono(16).save(OUT / "favicon-16x16.png")
    icono(32).save(OUT / "favicon-32x32.png")
    icono(48).save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    for nombre, lado in (("apple-touch-icon.png", 180), ("mstile-150x150.png", 150),
                         ("android-chrome-192x192.png", 192), ("android-chrome-512x512.png", 512)):
        img = icono(lado, fondo="#ffffff", margen=0.12)
        img.save(OUT / nombre)
        if nombre.startswith("android"):
            img.save(OUT / "icons" / nombre)
    icono(128).save(OUT / "icon-dark.png")
    icono(128).save(OUT / "icon-white.png")

    # Logotipos como archivo (tema claro / oscuro) y para correos
    (OUT / "logo.svg").write_text(
        logo_svg(m, 290, 60, m["COLOR_TEXTO"], m["COLOR_PRIMARIO"]), encoding="utf-8")
    (OUT / "logo-white.svg").write_text(
        logo_svg(m, 290, 60, "#ffffff", "#ffffff"), encoding="utf-8")
    (OUT / "icon-white.svg").write_text(icono_svg(m), encoding="utf-8")
    # Los PNG llevan solo el emblema (el nombre va como texto en el SVG y en el HTML del correo)
    for nombre in ("logo-dark@2x.png", "logo-white@2x.png", "email-logo.png", "emblema.png"):
        emblema(360).save(OUT / nombre)

    # Logotipos que se incrustan en el JavaScript de la bóveda (usan las clases de tema)
    (OUT / "inline-icon.svg").write_text(icono_svg(m), encoding="utf-8")
    (OUT / "inline-logo.svg").write_text(
        logo_svg(m, 290, 60, None, None, clase="tw-fill-marketing-logo"), encoding="utf-8")
    (OUT / "inline-logo-large.svg").write_text(
        logo_svg(m, 800, 200, None, None, clase="tw-fill-fg-nav"), encoding="utf-8")

    print(f"Imágenes generadas en {OUT}")


if __name__ == "__main__":
    main()
