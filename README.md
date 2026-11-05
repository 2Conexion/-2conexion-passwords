# 2Conexion Passwords: código fuente de las modificaciones

2Conexion Passwords es el servicio de gestión de contraseñas de **2Conexion Servicios Informaticos** (Aguascalientes, Ags., México; info@2conexion.com). Cada cliente tiene su propia bóveda, que funciona con las aplicaciones compatibles con Bitwarden (navegador, celular y escritorio).

Este repositorio publica, como piden sus licencias, el código fuente de lo que 2Conexion cambió en el software libre con que se construye el servicio. Aquí también están los enlaces a las fuentes originales exactas.

## De qué proyectos deriva

| Componente | Versión exacta que usamos | Licencia | ¿Lo modificamos? | Fuente original |
|---|---|---|---|---|
| **Vaultwarden** (servidor) | 1.37.5: imagen oficial `vaultwarden/server:1.37.5`, digest `sha256:4fe17f415f90087377d37c755e0ea3cf189dcc6794e49cdd2a9adbb4937d9e1f`, commit `6ed6921cc2b0e03b4d74189574d2a5e71c512e97` | AGPL-3.0 (`LICENSE-AGPL-3.0`) | **No.** Usamos el binario oficial sin cambios. Lo único que cambia es el contenido de las plantillas de correo y del panel, que Vaultwarden permite cargar desde una carpeta externa (`/templates`). Esas plantillas están en `plantillas/`. | https://github.com/dani-garcia/vaultwarden/tree/1.37.5 |
| **Bóveda web** (Bitwarden Web Vault, en la compilación de Vaultwarden) | v2026.10.1, la que trae la imagen 1.37.5. Archivo `bw_web_v2026.10.1.tar.gz`, SHA-256 `354de9056c871e48db84975985e7d57c111ac6537bd4e4720488019e8638060f` | GPL-3.0 (`LICENSE`) | **Sí.** Lleva la marca, las traducciones al español y los estilos de 2Conexion (ver `CAMBIOS.md`). | Compilación: https://github.com/dani-garcia/bw_web_builds/releases/tag/v2026.10.1 · Código de los clientes de Bitwarden: https://github.com/bitwarden/clients |

## Contenido

| Ruta | Qué es | Licencia |
|---|---|---|
| `construir-web-vault.py` | Toma la bóveda web original de la imagen `vaultwarden/server:<versión>` y le aplica la marca de `branding/`. El resultado es exactamente la bóveda web que servimos. | GPL-3.0 |
| `construir-plantillas.py` | Descarga las plantillas originales de Vaultwarden de esa versión, traduce los correos al español y les pone la marca. El resultado queda en `plantillas/<versión>/`. | AGPL-3.0 |
| `branding/marca.env` | Nombre, colores e idioma de la marca. | GPL-3.0 |
| `branding/generar-imagenes.py`, `branding/icono-origen.png`, `branding/images/` | Generador de imágenes y los logotipos e íconos de 2Conexion Passwords. | GPL-3.0 (ver "Marcas") |
| `branding/traducciones/es/` | Traducciones al español que completan las de la bóveda web. | GPL-3.0 |
| `branding/templates/` | Encabezado y pie de los correos, y la hoja de estilos `user.vaultwarden.scss.hbs`. | AGPL-3.0 |
| `branding/originales/<versión>/` | Copia sin cambios de las plantillas originales de Vaultwarden (`src/static/templates`), para comparar. | AGPL-3.0 |
| `plantillas/1.37.5/` | Las plantillas que usamos, ya generadas: correos, estilos y panel. | AGPL-3.0 |

## Cómo reproducir la bóveda web y las plantillas

Requisitos: Docker, Python 3 y Pillow (este último solo para `generar-imagenes.py`).

```bash
docker pull vaultwarden/server:1.37.5
python3 construir-web-vault.py 1.37.5     # deja web-vault/1.37.5/
python3 construir-plantillas.py 1.37.5    # deja plantillas/1.37.5/
```

Después se monta `web-vault/1.37.5` como `/web-vault` y `plantillas/1.37.5` como `/templates` en el contenedor oficial de Vaultwarden. Si una versión nueva cambia algo de lo que se reemplaza, los scripts terminan con error y no dejan una bóveda a medias.

No están en este repositorio, porque no derivan de Vaultwarden ni de Bitwarden: la configuración de cada servidor, las credenciales y los programas internos de 2Conexion (facturación, alta de clientes y respaldos), que se comunican con Vaultwarden por la red. ⚖️ [Por validar con un abogado especialista en licencias libres.]

## Aviso de no afiliación

2Conexion Passwords **no es un producto de Bitwarden, Inc.** ni del proyecto Vaultwarden, y ninguno de los dos lo respalda ni le da soporte. Para cualquier duda del servicio, escribe a info@2conexion.com, no a esos proyectos.

- **Vaultwarden** es un proyecto de código abierto de Daniel García y sus colaboradores.
- La **bóveda web** se basa en los clientes de Bitwarden, de Bitwarden, Inc. y sus colaboradores, en la compilación que mantiene el proyecto Vaultwarden.
- "Bitwarden" es una marca registrada de Bitwarden, Inc. Aquí solo se usa para describir con qué es compatible el servicio.

## Marcas

El nombre "2Conexion", el nombre "2Conexion Passwords" y sus logotipos identifican a 2Conexion. Puedes redistribuir y modificar los archivos de este repositorio conforme a su licencia. Conforme a la sección 7, inciso e), de la GPL-3.0 y de la AGPL-3.0, esas licencias no te dan derecho a usar esas marcas para identificar otro servicio: si publicas una versión modificada, cámbiale el nombre y los logotipos. ⚖️ [Por validar con un abogado.]

## Licencias

- `LICENSE`: GNU General Public License v3 (GPL-3.0), la misma de los clientes de Bitwarden.
- `LICENSE-AGPL-3.0`: GNU Affero General Public License v3 (AGPL-3.0), la misma de Vaultwarden 1.37.5.

Este software se ofrece **sin garantía**, conforme a esas licencias. Eso no limita las obligaciones de 2Conexion como proveedor del servicio frente a sus clientes.

## Versiones

Cada vez que se cambie la versión de Vaultwarden o de la bóveda web, este repositorio se actualiza y se agrega una etiqueta con la versión de Vaultwarden (por ejemplo, `vw-1.37.5`).
