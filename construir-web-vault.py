#!/usr/bin/env python3
"""Construye la bóveda web con la marca para una versión de Vaultwarden.

Uso: construir-web-vault.py 1.37.4

Extrae /web-vault de la imagen vaultwarden/server:<versión>, aplica la marca de
branding/ y deja el resultado en web-vault/<versión>/ (se monta en los contenedores
de los clientes). Si una versión nueva cambia algo que aquí se reemplaza, el script
falla en lugar de dejar una bóveda a medio marcar.
"""
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
BRANDING = BASE / "branding"

# Claves de traducción que nombran al sitio (no a las apps de Bitwarden, que sí se llaman así)
CLAVES_SITIO = ("bitWebVault",)


# Aviso de atribución que la bóveda muestra al pie, por idioma (se deja vacío y se
# oculta con ESTILO_INDEX; la licencia y el código fuente se ofrecen en los términos del servicio)
PIE = {
    "es": {
        " A modified version of the Bitwarden\u00ae Web Vault for Vaultwarden (an unofficial rewrite of the Bitwarden\u00ae server).":
            "",
        " Vaultwarden is not associated with the Bitwarden\u00ae project nor Bitwarden Inc. ":
            "",
    },
}


# Textos que se reemplazan siempre (aunque ya vengan traducidos de origen) porque
# nombran a Bitwarden como si fuera el servicio. {MARCA} se sustituye por la marca.
FORZADAS = {
    "es": {
        "viewSendHiddenEmailWarning": "El usuario de {MARCA} que creó este Send decidió ocultar su dirección de "
            "correo electrónico. Asegúrate de que confías en el origen de este enlace antes de usar o descargar "
            "su contenido.",
        "sendAccessCreatorIdentifier": "El usuario de {MARCA} $USER_IDENTIFIER$ compartió contigo lo siguiente",
        "sendAccessTaglineProductDesc": "Send de {MARCA} comparte información sensible y temporal de forma fácil y segura.",
        "disableSendPolicyDesc": "No permitir a los usuarios crear o editar un Send. Eliminar un Send existente "
            "todavía está permitido.",
    },
}

# Estilos que van en index.html para que apliquen desde el primer instante, antes de que
# cargue la aplicación (la pantalla de carga previa traía el fondo blanco y las
# ilustraciones de Vaultwarden)
ESTILO_INDEX = (
    "<style>"
    # Lo mínimo para pintar la pantalla de carga sin esperar a los estilos completos
    # (que se mueven al final del body para que no bloqueen la primera pintura)
    "html{background:#ebf3f0}html.theme_dark{background:#10262b}body{margin:0}"
    "body>app-root>div.tw-min-h-\\[100vh\\]{min-height:100vh;background:linear-gradient(155deg,#e3f0f3 0%,#f3f8f4 50%,#e4efdc 100%) fixed}"
    ".theme_dark body>app-root>div.tw-min-h-\\[100vh\\]{background:linear-gradient(155deg,#0c2329 0%,#10262b 50%,#16291d 100%) fixed}"
    "body>app-root>div>div.tw-fixed{position:fixed;padding:1.25rem 1.25rem 0}"
    "img.new-logo-themed{display:block;width:200px}"
    ".theme_light img.new-logo-themed{content:url(images/logo.svg)}"
    ".theme_dark img.new-logo-themed{content:url(images/logo-white.svg)}"
    # Enlace "Más información" del aviso de Send: lleva a la ayuda de bitwarden.com
    'a[href="https://bitwarden.com/help/receive-send/"]{display:none!important}'
    # Renglón del aviso de atribución en el pie (vacío)
    "bit-landing-footer footer>div:last-child{display:none!important}"
    "</style>"
)

# Nombres de otros productos de Bitwarden que no se cambian por la marca
BITWARDEN_SE_QUEDA = ("Bitwarden Authenticator", "Bitwarden Secrets Manager", "Bitwarden Directory Connector")


def leer_marca():
    marca = {}
    for linea in (BRANDING / "marca.env").read_text(encoding="utf-8").splitlines():
        if "=" in linea and not linea.lstrip().startswith("#"):
            k, v = linea.split("=", 1)
            marca[k.strip()] = v.strip().strip('"')
    return marca


def js_str(texto):
    """Texto listo para ir dentro de una cadena JS entre comillas dobles (solo ASCII)."""
    return json.dumps(texto, ensure_ascii=True)[1:-1]


def reemplazar(texto, viejo, nuevo, minimo, donde):
    n = texto.count(viejo)
    if n < minimo:
        sys.exit(f"ERROR: en {donde} se esperaban al menos {minimo} apariciones de {viejo!r} y hay {n}. "
                 "La bóveda web cambió; hay que ajustar construir-web-vault.py.")
    return texto.replace(viejo, nuevo)


def extraer(version, destino):
    imagen = f"vaultwarden/server:{version}"
    cid = subprocess.run(["docker", "create", imagen], check=True,
                         capture_output=True, text=True).stdout.strip()
    try:
        subprocess.run(["docker", "cp", f"{cid}:/web-vault/.", str(destino)], check=True)
    finally:
        subprocess.run(["docker", "rm", cid], check=True, capture_output=True)
    for mapa in destino.rglob("*.map"):
        mapa.unlink()


def marcar_index(destino, m, sello):
    ruta = destino / "index.html"
    html = ruta.read_text(encoding="utf-8")
    html = reemplazar(html, "<title page-title>Vaultwarden Web</title>",
                      f"<title page-title>{m['MARCA']}</title>", 1, "index.html")
    html = reemplazar(html, 'alt="Vaultwarden"', f'alt="{m["MARCA"]}"', 1, "index.html")
    html = reemplazar(html, 'name="theme-color" content="#175DDC"',
                      f'name="theme-color" content="{m["COLOR_PRIMARIO"]}"', 1, "index.html")
    # Sin el ícono monocromático de Safari (es el de Vaultwarden); Safari usa entonces el ícono normal
    html = re.sub(r'<link rel="mask-icon"[^>]*/>', "", html)
    # Sello de construcción en el script principal: su nombre no cambia al reconstruir
    # y el navegador seguiría usando la copia que tiene guardada
    html, n = re.subn(r'(src="app/main\.[0-9a-f]+\.js)"', rf'\1?m={sello}"', html)
    if n != 1:
        sys.exit(f"ERROR: se esperaba 1 referencia a app/main.*.js en index.html y hay {n}")
    # Pantalla de carga previa: sin las dos ilustraciones de las esquinas
    html, n = re.subn(r'<div class="tw-hidden md:tw-block \[&_svg\]:tw-absolute[^"]*"><svg.*?</svg></div>', "", html,
                      flags=re.S)
    if n != 2:
        sys.exit(f"ERROR: se esperaban 2 ilustraciones en la pantalla de carga de index.html y hay {n}")
    html = reemplazar(html, "</head>", ESTILO_INDEX + "</head>", 1, "index.html")
    # Hojas de estilo al final del body: la pantalla de carga se pinta de inmediato con
    # ESTILO_INDEX y los scripts (defer) igual esperan a que estas hojas terminen de cargar
    hojas = re.findall(r'<link href="styles\.[0-9a-f]+\.css" rel="stylesheet">', html)
    hojas += re.findall(r'<link rel="stylesheet" href="css/vaultwarden\.css"/>', html)
    if len(hojas) != 2:
        sys.exit(f"ERROR: se esperaban 2 hojas de estilo en index.html y hay {len(hojas)}")
    for hoja in hojas:
        html = html.replace(hoja, "", 1)
    html = reemplazar(html, "</app-root>", "</app-root>" + "".join(hojas), 1, "index.html")
    html = reemplazar(html, '<html class="theme_light">',
                      f'<html lang="{m["IDIOMA"]}" class="theme_light">', 1, "index.html")
    ruta.write_text(html, encoding="utf-8")
    return html


def marcar_manifiestos(destino, html, m):
    nombres = {"manifest.json"}
    nombres.update(re.findall(r'rel="manifest" href="([^"]+)"', html))
    for nombre in nombres:
        ruta = destino / nombre
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        datos["name"] = m["MARCA"]
        datos["short_name"] = m["MARCA_LINEA2"]
        datos["theme_color"] = m["COLOR_PRIMARIO"]
        ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def marcar_js(destino, m):
    principales = list((destino / "app").glob("main.*.js"))
    if len(principales) != 1:
        sys.exit(f"ERROR: se esperaba un solo app/main.*.js y hay {len(principales)}")
    ruta = principales[0]
    js = ruta.read_text(encoding="utf-8")
    js = reemplazar(js, '"Vaultwarden Web"', f'"{js_str(m["MARCA"])}"', 3, ruta.name)
    js = reemplazar(js, '"alt","Vaultwarden"', f'"alt","{js_str(m["MARCA"])}"', 1, ruta.name)
    js = reemplazar(js, "otpauth://totp/Vaultwarden:",
                    f"otpauth://totp/{m['MARCA_OTP'].replace(' ', '%20')}:", 1, ruta.name)

    # Idioma inicial: en lugar del idioma del navegador se usa el de marca.env.
    # Cada usuario puede cambiarlo después en Ajustes > Preferencias.
    js, n = re.subn(r"useFactory:(\w+)=>\1\.navigator\.language",
                    lambda x: f'useFactory:{x.group(1)}=>"{m["IDIOMA"]}"', js)
    if n != 1:
        sys.exit(f"ERROR: se esperaba 1 lectura del idioma del navegador en {ruta.name} y hay {n}")

    # Aviso de atribución del pie (se conserva, traducido)
    for ingles, traducido in PIE.get(m["IDIOMA"], {}).items():
        js = reemplazar(js, ingles, js_str(traducido), 1, ruta.name)

    # Logotipos incrustados como SVG: se identifican por su viewBox
    for viewbox, archivo in (("0 0 60 60", "inline-icon.svg"),
                             ("0 0 290 60", "inline-logo.svg"),
                             ("0 0 800 200", "inline-logo-large.svg")):
        nuevo = (BRANDING / "images" / archivo).read_text(encoding="utf-8")
        if "`" in nuevo or "${" in nuevo or "\\" in nuevo:
            sys.exit(f"ERROR: {archivo} contiene caracteres que rompen la plantilla JS")
        patron = re.compile(r'<svg version="1\.1" viewBox="' + re.escape(viewbox) + r'"[^`]*?</svg>')
        js, n = patron.subn(lambda _: nuevo, js)
        if n != 1:
            sys.exit(f"ERROR: se esperaba 1 logo incrustado con viewBox {viewbox} y hay {n}")
    ruta.write_text(js, encoding="utf-8")


def marcar_traducciones(destino, m):
    tocadas = 0
    for ruta in (destino / "locales").glob("*/messages.json"):
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        cambio = False
        for clave in CLAVES_SITIO:
            mensaje = datos.get(clave, {}).get("message", "")
            if "Bitwarden" in mensaje:
                datos[clave]["message"] = mensaje.replace("Bitwarden", m["MARCA"])
                cambio = True
        if cambio:
            ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
            tocadas += 1
    if tocadas == 0:
        sys.exit("ERROR: no se encontró ninguna traducción que marcar")


def aplicar_traducciones(destino, m):
    """Completa la traducción del idioma de la marca con branding/traducciones/<idioma>/*.json.

    Solo se aplica a textos que en esta versión siguen sin traducir (faltan o están
    idénticos al inglés), para no pisar traducciones oficiales nuevas.
    """
    idioma = m["IDIOMA"]
    carpeta = BRANDING / "traducciones" / idioma
    if idioma == "en" or not carpeta.is_dir():
        return
    ruta = destino / "locales" / idioma / "messages.json"
    actual = json.loads(ruta.read_text(encoding="utf-8"))
    ingles = json.loads((destino / "locales" / "en" / "messages.json").read_text(encoding="utf-8"))
    variables = re.compile(r"\$[A-Z0-9_]+\$")

    aplicadas, descartadas = 0, []
    for archivo in sorted(carpeta.glob("[0-9]*.json")):
        for clave, texto in json.loads(archivo.read_text(encoding="utf-8")).items():
            if clave not in ingles:
                continue  # el texto ya no existe en esta versión
            original = ingles[clave]["message"]
            if sorted(variables.findall(original)) != sorted(variables.findall(texto)):
                descartadas.append(clave)
                continue
            if clave in actual and actual[clave]["message"] != original:
                continue  # ya viene traducido de origen
            actual[clave] = {**ingles[clave], "message": texto}
            aplicadas += 1

    reemplazos = carpeta / "_reemplazos.json"
    if reemplazos.exists():
        for viejo, nuevo in json.loads(reemplazos.read_text(encoding="utf-8")).items():
            for entrada in actual.values():
                entrada["message"] = entrada["message"].replace(viejo, nuevo)

    # "Bitwarden" en el resto de los textos se cambia por la marca (los enlaces de ayuda
    # siguen llevando a bitwarden.com)
    for entrada in actual.values():
        texto = entrada["message"]
        if "Bitwarden" not in texto:
            continue
        for i, nombre in enumerate(BITWARDEN_SE_QUEDA):
            texto = texto.replace(nombre, f"\x00{i}\x00")
        texto = texto.replace("Bitwarden", m["MARCA"])
        for i, nombre in enumerate(BITWARDEN_SE_QUEDA):
            texto = texto.replace(f"\x00{i}\x00", nombre)
        entrada["message"] = texto

    for clave, texto in FORZADAS.get(idioma, {}).items():
        if clave not in ingles:
            sys.exit(f"ERROR: el texto {clave} ya no existe en esta versión; hay que ajustar FORZADAS")
        actual[clave] = {**ingles[clave], "message": texto.replace("{MARCA}", m["MARCA"])}

    ruta.write_text(json.dumps(actual, ensure_ascii=False, indent=2), encoding="utf-8")
    pendientes = sum(1 for c, v in ingles.items()
                     if re.search(r"[A-Za-z]{4}", variables.sub("", v["message"]))
                     and " " in v["message"].strip()
                     and actual.get(c, {}).get("message") == v["message"])
    print(f"Traducción ({idioma}): {aplicadas} textos aplicados, {pendientes} frases siguen en inglés")
    if descartadas:
        print(f"  AVISO: {len(descartadas)} traducciones descartadas porque sus variables ya no coinciden: "
              + ", ".join(descartadas[:15]))


def copiar_imagenes(destino):
    origen = BRANDING / "images"
    for archivo in origen.rglob("*"):
        if archivo.is_dir() or archivo.name.startswith("inline-"):
            continue
        relativo = archivo.relative_to(origen)
        final = destino / relativo if archivo.name == "favicon.ico" else destino / "images" / relativo
        final.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(archivo, final)


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        sys.exit(__doc__)
    version = sys.argv[1]
    m = leer_marca()
    final = BASE / "web-vault" / version
    temporal = BASE / "web-vault" / f".{version}.tmp"
    if temporal.exists():
        shutil.rmtree(temporal)
    temporal.mkdir(parents=True)

    extraer(version, temporal)
    sello = time.strftime("%Y%m%d%H%M%S")
    html = marcar_index(temporal, m, sello)
    marcar_manifiestos(temporal, html, m)
    marcar_js(temporal, m)
    marcar_traducciones(temporal, m)
    aplicar_traducciones(temporal, m)
    copiar_imagenes(temporal)
    (temporal / "marca-blanca.json").write_text(
        json.dumps({"marca": m["MARCA"], "vaultwarden": version}, ensure_ascii=False), encoding="utf-8")

    restantes = [str(p.relative_to(temporal)) for p in (temporal / "index.html", *temporal.glob("*.json"))
                 if "Vaultwarden Web" in p.read_text(encoding="utf-8", errors="ignore")]
    if restantes:
        sys.exit(f"ERROR: quedó 'Vaultwarden Web' en {restantes}")

    # El contenido se copia dentro de la carpeta existente (sin reemplazarla) para no
    # romper el montaje de los contenedores que ya la estén usando
    final.mkdir(exist_ok=True)
    subprocess.run(["cp", "-a", f"{temporal}/.", str(final)], check=True)
    shutil.rmtree(temporal)
    subprocess.run(["chmod", "-R", "a+rX", str(final)], check=True)
    print(f"Bóveda web con marca lista en {final}")


if __name__ == "__main__":
    main()
