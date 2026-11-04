# Cambios respecto a los originales

Este archivo lista lo que se modificó respecto a Vaultwarden 1.37.5 y a la bóveda web v2026.10.1 de `bw_web_builds`. El detalle exacto está en el código de `construir-web-vault.py` y de `construir-plantillas.py`.

## 1. Servidor Vaultwarden 1.37.5

**No se modificó el programa.** Se usa la imagen oficial `vaultwarden/server:1.37.5` (digest `sha256:4fe17f41…d9e1f`). Vaultwarden permite cargar plantillas externas desde `/templates`, y lo único que cambia es su contenido (sección 3).

## 2. Bóveda web v2026.10.1 (GPL-3.0): `construir-web-vault.py`

El script toma `/web-vault` de la imagen oficial, borra los mapas de código fuente (`*.map`) y hace estos cambios:

**`index.html`**
- El título "Vaultwarden Web" y el texto alternativo del logo cambian a "2Conexión Passwords".
- `theme-color` cambia a `#1f6170`.
- Se quita el ícono `mask-icon` de Safari.
- Se agrega `lang="es"`.
- Al script principal se le agrega un sello de construcción (`?m=AAAAMMDDhhmmss`) para que los navegadores no usen una copia vieja.
- La pantalla de carga pierde las dos ilustraciones de las esquinas.
- Se agregan estilos en línea: fondo con los colores de la marca, logo de 2Conexión y ocultar el enlace "Más información" de Send, que lleva a bitwarden.com.
- Las dos hojas de estilo pasan al final del `<body>`.

**`manifest.json`**: nombre, nombre corto y color de la marca.

**`app/main.*.js`**
- "Vaultwarden Web" pasa a ser "2Conexión Passwords", en el título, en el texto alternativo y en el pie.
- El emisor de los códigos TOTP (`otpauth://totp/`) pasa a ser "2Conexion Passwords".
- El idioma inicial ya no es el del navegador, sino el de `marca.env` (`es`). Cada usuario puede cambiarlo en Ajustes > Preferencias.
- Los tres logotipos SVG incrustados (viewBox `0 0 60 60`, `0 0 290 60` y `0 0 800 200`) se sustituyen por los de `branding/images/inline-*.svg`.
- **Aviso de atribución del pie.** En la versión actual, sus dos frases ("A modified version of the Bitwarden® Web Vault for Vaultwarden…" y "Vaultwarden is not associated with the Bitwarden® project nor Bitwarden Inc.") se dejan vacías y el renglón se oculta con CSS. ⚠️ Está previsto restaurarlo en español, con la dirección de este repositorio, antes de que el servicio se ofrezca al público.

**`locales/*/messages.json`**
- En la clave `bitWebVault`, "Bitwarden" pasa a ser "2Conexión Passwords" en todos los idiomas.
- En español (`locales/es`):
  - se completan los textos que siguen sin traducir con `branding/traducciones/es/0*.json`, sin sobrescribir las traducciones oficiales;
  - con `_reemplazos.json`, "caja fuerte" pasa a ser "bóveda";
  - "Bitwarden" pasa a ser "2Conexión Passwords" cuando se refiere al servicio. Se conservan "Bitwarden Authenticator", "Bitwarden Secrets Manager" y "Bitwarden Directory Connector", y los enlaces de ayuda siguen llevando a bitwarden.com;
  - se reescriben 4 textos de Send y de políticas (`FORZADAS`).

**Imágenes**: se copian a `images/` los archivos de `branding/images/` (íconos, logotipos y `favicon.ico`).

**Archivo nuevo**: `marca-blanca.json`, con la marca y la versión de Vaultwarden.

## 3. Plantillas de Vaultwarden 1.37.5 (AGPL-3.0): `construir-plantillas.py`

Los originales se descargan de `src/static/templates/{email,admin}` de la etiqueta 1.37.5 y se guardan sin cambios en `branding/originales/1.37.5/`.

- **Correos (`plantillas/1.37.5/email/`)**
  - Los asuntos y los textos se traducen al español con la tabla `TRADUCCIONES`.
  - El color de los botones pasa de `#3c8dbc` a `#1f6170`.
  - `email_header.hbs`, `email_footer.hbs` y `email_footer_text.hbs` se reemplazan por los de la marca (`branding/templates/email/`).
- **Panel (`plantillas/1.37.5/admin/base.hbs`)**: el favicon, el título ("2Conexión Passwords - Administración") y el nombre con el emblema.
- **Estilos (`plantillas/1.37.5/scss/user.vaultwarden.scss.hbs`)**: es la hoja de estilos de la marca. Es un archivo de personalización que Vaultwarden prevé.

## 4. Lo que no se cambió

- La criptografía, la sincronización, la API, el almacenamiento y cualquier otra lógica de Vaultwarden o de la bóveda web.
- Las aplicaciones de Bitwarden para navegador, celular y escritorio: se usan las oficiales.
