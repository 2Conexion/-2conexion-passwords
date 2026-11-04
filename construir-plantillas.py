#!/usr/bin/env python3
"""Construye las plantillas (correos, estilos y panel /admin) de una versión de Vaultwarden.

Uso: construir-plantillas.py 1.37.4

Deja el resultado en plantillas/<versión>/, que se monta como /templates en las bóvedas:
  email/  correos traducidos al español, con el encabezado y pie de branding/templates/email/
  scss/   estilos de la marca (branding/templates/scss/)
  admin/  página base del panel /admin con el ícono y nombre de la marca

Los originales en inglés se descargan del código de Vaultwarden a branding/originales/<versión>/.
Si una versión nueva agrega o cambia textos de correo, el script termina con error y lista lo
que falta traducir en TRADUCCIONES; no deja plantillas a medias.
"""
import io
import re
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
BRANDING = BASE / "branding"
MARCA = "2Conexión Passwords"
SEPARADOR = "<!---------------->"
# Color de los botones de los correos (el original es un azul de Bitwarden)
COLOR_BOTON_ORIGINAL = "#3c8dbc"
COLOR_BOTON = "#1f6170"
# Archivos de correo hechos a mano para la marca (no se traducen ni se descargan)
PROPIOS = ("email_header.hbs", "email_footer.hbs", "email_footer_text.hbs")

TRADUCCIONES = {
    # --- recuperación de cuenta por el administrador
    "Admin account recovery from {{org_name}} organization":
        "Recuperación de cuenta por el administrador de {{org_name}}",
    "The master password for {{user_name}} has been changed.":
        "La contraseña maestra de {{user_name}} fue cambiada.",
    "The master password for <b>{{user_name}}</b> has been changed.":
        "La contraseña maestra de <b>{{user_name}}</b> fue cambiada.",
    "Your two-step verification providers have been reset.":
        "Tus métodos de verificación en dos pasos fueron restablecidos.",
    "Email two factor has been activated as a fallback.":
        "Se activó la verificación por correo como respaldo.",
    "If you did not initiate this request, please reach out to your administrator immediately.":
        "Si no solicitaste esto, contacta a tu administrador de inmediato.",

    # --- cambio de correo
    "Your Email Change": "Cambio de tu correo electrónico",
    "To finalize changing your email address enter the following code in web vault: {{token}}":
        "Para terminar de cambiar tu correo, escribe este código en la bóveda web: {{token}}",
    "To finalize changing your email address enter the following code in web vault: <b>{{token}}</b>":
        "Para terminar de cambiar tu correo, escribe este código en la bóveda web: <b>{{token}}</b>",
    "If you did not try to change your email address, contact your administrator.":
        "Si no intentaste cambiar tu correo, contacta a tu administrador.",
    "A user ({{ acting_address }}) recently tried to change their account to use this email address ({{ existing_address }}). An account already exists with this email ({{ existing_address }}).":
        "Un usuario ({{ acting_address }}) intentó cambiar su cuenta para usar este correo ({{ existing_address }}). Ya existe una cuenta con este correo ({{ existing_address }}).",
    "If you did not try to change an email address, contact your administrator.":
        "Si no intentaste cambiar un correo, contacta a tu administrador.",
    "A user ({{ acting_address }}) recently tried to change their account to use this email address ({{ existing_address }}). You already have been invited to join Vaultwarden using this address.":
        "Un usuario ({{ acting_address }}) intentó cambiar su cuenta para usar este correo ({{ existing_address }}). Ya tienes una invitación a " + MARCA + " con esta dirección.",
    "To change your email address you first would have to delete the account associated with this email address ({{ existing_address }}):":
        "Para cambiar tu correo, primero tendrías que eliminar la cuenta asociada a esta dirección ({{ existing_address }}):",
    "Request account deletion: {{url}}/#/recover-delete":
        "Solicitar eliminación de la cuenta: {{url}}/#/recover-delete",
    "Once that is done you can change the email address of your existing account to this address. Any invitation would have to be redone.":
        "Después podrás cambiar el correo de tu cuenta actual a esta dirección. Las invitaciones tendrían que enviarse de nuevo.",
    "Request account deletion": "Solicitar eliminación de la cuenta",

    # --- eliminar cuenta
    "Delete Your Account": "Eliminar tu cuenta",
    "Click the link below to delete your account.":
        "Haz clic en el siguiente enlace para eliminar tu cuenta.",
    "Delete Your Account: {{url}}/#/verify-recover-delete?userId={{user_id}}&token={{token}}&email={{email}}":
        "Eliminar tu cuenta: {{url}}/#/verify-recover-delete?userId={{user_id}}&token={{token}}&email={{email}}",
    "If you did not request this email to delete your account, you can safely ignore this email.":
        "Si no solicitaste eliminar tu cuenta, puedes ignorar este correo.",

    # --- acceso de emergencia
    "Emergency access contact {{{grantee_email}}} accepted":
        "{{{grantee_email}}} aceptó ser tu contacto de emergencia",
    "This email is to notify you that {{grantee_email}} has accepted your invitation to become an emergency access contact.":
        "Te avisamos que {{grantee_email}} aceptó tu invitación para ser contacto de acceso de emergencia.",
    "To confirm this user, log into the web vault ({{url}}), go to settings and confirm the user.":
        "Para confirmar a este usuario, entra a la bóveda web ({{url}}), ve a Ajustes y confírmalo.",
    "If you do not wish to confirm this user, you can also remove them on the same page.":
        "Si no deseas confirmarlo, puedes quitarlo en esa misma página.",
    "To confirm this user, log into the": "Para confirmar a este usuario, entra a la",
    "web vault": "bóveda web",
    ", go to settings and confirm the user.": ", ve a Ajustes y confírmalo.",
    "Emergency access contact for {{{grantor_name}}} confirmed":
        "Ya eres contacto de emergencia de {{{grantor_name}}}",
    "This email is to notify you that you have been confirmed as an emergency access contact for *{{grantor_name}}*.":
        "Te avisamos que fuiste confirmado como contacto de acceso de emergencia de *{{grantor_name}}*.",
    "This email is to notify you that you have been confirmed as an emergency access contact for <b>{{grantor_name}}</b>.":
        "Te avisamos que fuiste confirmado como contacto de acceso de emergencia de <b>{{grantor_name}}</b>.",
    "You can now initiate emergency access requests from the web vault ({{url}}).":
        "Ya puedes iniciar solicitudes de acceso de emergencia desde la bóveda web ({{url}}).",
    "You can now initiate emergency access requests from the":
        "Ya puedes iniciar solicitudes de acceso de emergencia desde la",
    "Emergency access request for {{{grantor_name}}} approved":
        "Solicitud de acceso de emergencia a {{{grantor_name}}} aprobada",
    "{{grantor_name}} has approved your emergency access request. You may now login on the web vault ({{url}}) and access their account.":
        "{{grantor_name}} aprobó tu solicitud de acceso de emergencia. Ya puedes entrar a la bóveda web ({{url}}) y acceder a su cuenta.",
    "<b>{{grantor_name}}</b> has approved your emergency access request. You may now login on the":
        "<b>{{grantor_name}}</b> aprobó tu solicitud de acceso de emergencia. Ya puedes entrar a la",
    "and access their account.": "y acceder a su cuenta.",
    "Emergency access request by {{{grantee_name}}} initiated":
        "{{{grantee_name}}} inició una solicitud de acceso de emergencia",
    "{{grantee_name}} has initiated an emergency access request to {{atype}} your account. You may login on the web vault ({{url}}) and manually approve or reject this request.":
        "{{grantee_name}} inició una solicitud de acceso de emergencia a tu cuenta (tipo: {{atype}}). Puedes entrar a la bóveda web ({{url}}) y aprobarla o rechazarla.",
    "<b>{{grantee_name}}</b> has initiated an emergency access request to <b>{{atype}}</b> your account. You may login on the":
        "<b>{{grantee_name}}</b> inició una solicitud de acceso de emergencia a tu cuenta (tipo: <b>{{atype}}</b>). Puedes entrar a la",
    "and manually approve or reject this request.": "y aprobarla o rechazarla.",
    "If you do nothing, the request will automatically be approved after {{wait_time_days}} day(s).":
        "Si no haces nada, la solicitud se aprobará automáticamente en {{wait_time_days}} día(s).",
    "If you do nothing, the request will automatically be approved after <b>{{wait_time_days}}</b> day(s).":
        "Si no haces nada, la solicitud se aprobará automáticamente en <b>{{wait_time_days}}</b> día(s).",
    "Emergency access request to {{{grantor_name}}} rejected":
        "Solicitud de acceso de emergencia a {{{grantor_name}}} rechazada",
    "{{grantor_name}} has rejected your emergency access request.":
        "{{grantor_name}} rechazó tu solicitud de acceso de emergencia.",
    "<b>{{grantor_name}}</b> has rejected your emergency access request.":
        "<b>{{grantor_name}}</b> rechazó tu solicitud de acceso de emergencia.",
    "Emergency access request by {{{grantee_name}}} is pending":
        "Solicitud de acceso de emergencia de {{{grantee_name}}} pendiente",
    "{{grantee_name}} has a pending emergency access request to {{atype}} your account. You may login on the web vault ({{url}}) and manually approve or reject this request.":
        "{{grantee_name}} tiene pendiente una solicitud de acceso de emergencia a tu cuenta (tipo: {{atype}}). Puedes entrar a la bóveda web ({{url}}) y aprobarla o rechazarla.",
    "<b>{{grantee_name}}</b> has a pending emergency access request to <b>{{atype}}</b> your account. You may login on the":
        "<b>{{grantee_name}}</b> tiene pendiente una solicitud de acceso de emergencia a tu cuenta (tipo: <b>{{atype}}</b>). Puedes entrar a la",
    "If you do nothing, the request will automatically be approved after {{days_left}} day(s).":
        "Si no haces nada, la solicitud se aprobará automáticamente en {{days_left}} día(s).",
    "If you do nothing, the request will automatically be approved after <b>{{days_left}}</b> day(s).":
        "Si no haces nada, la solicitud se aprobará automáticamente en <b>{{days_left}}</b> día(s).",
    "Emergency access request by {{{grantee_name}}} granted":
        "Se concedió acceso de emergencia a {{{grantee_name}}}",
    "{{grantee_name}} has been granted emergency access to {{atype}} your account. You may login on the web vault ({{url}}) and manually revoke this request.":
        "{{grantee_name}} obtuvo acceso de emergencia a tu cuenta (tipo: {{atype}}). Puedes entrar a la bóveda web ({{url}}) y revocarlo.",
    "<b>{{grantee_name}}</b> has been granted emergency access to <b>{{atype}}</b> your account. You may login on the":
        "<b>{{grantee_name}}</b> obtuvo acceso de emergencia a tu cuenta (tipo: <b>{{atype}}</b>). Puedes entrar a la",
    "and manually revoke this request.": "y revocarlo.",
    "Emergency access for {{{grantor_name}}}": "Acceso de emergencia para {{{grantor_name}}}",
    "You have been invited to become an emergency contact for {{grantor_name}}. To accept this invite, click the following link:":
        "{{grantor_name}} te invitó a ser su contacto de emergencia. Para aceptar, haz clic en el siguiente enlace:",
    "You have been invited to become an emergency contact for <b>{{grantor_name}}</b>.":
        "<b>{{grantor_name}}</b> te invitó a ser su contacto de emergencia.",
    "If you do not wish to become an emergency contact for {{grantor_name}}, you can safely ignore this email.":
        "Si no deseas ser contacto de emergencia de {{grantor_name}}, puedes ignorar este correo.",
    "Become emergency contact": "Aceptar ser contacto de emergencia",

    # --- inicios de sesión y dispositivos
    "Incomplete Two-Step Login From {{{device_name}}}":
        "Inicio de sesión en dos pasos incompleto desde {{{device_name}}}",
    "Someone attempted to log into your account with the correct master password, but did not provide the correct token or action required to complete the two-step login process within {{time_limit}} minutes of the initial login attempt.":
        "Alguien intentó entrar a tu cuenta con la contraseña maestra correcta, pero no completó la verificación en dos pasos dentro de los {{time_limit}} minutos siguientes al intento.",
    "* Date: {{datetime}}": "* Fecha: {{datetime}}",
    "* IP Address: {{ip}}": "* Dirección IP: {{ip}}",
    "* Device Name: {{device_name}}": "* Dispositivo: {{device_name}}",
    "* Device Type: {{device_type}}": "* Tipo de dispositivo: {{device_type}}",
    "If this was not you or someone you authorized, then you should change your master password as soon as possible, as it is likely to be compromised.":
        "Si no fuiste tú ni alguien autorizado por ti, cambia tu contraseña maestra cuanto antes, porque probablemente está comprometida.",
    "<b>Date</b>: {{datetime}}": "<b>Fecha</b>: {{datetime}}",
    "<b>Date:</b> {{datetime}}": "<b>Fecha:</b> {{datetime}}",
    "<b>IP Address:</b> {{ip}}": "<b>Dirección IP:</b> {{ip}}",
    "<b>Device Name:</b> {{device_name}}": "<b>Dispositivo:</b> {{device_name}}",
    "<b>Device Type:</b> {{device_type}}": "<b>Tipo de dispositivo:</b> {{device_type}}",
    "New Device Logged In From {{{device_name}}}":
        "Nuevo inicio de sesión desde {{{device_name}}}",
    "Your account was just logged into from a new device.":
        "Se acaba de iniciar sesión en tu cuenta desde un dispositivo nuevo.",
    "You can deauthorize all devices that have access to your account from the web vault ( {{url}} ) under Settings > My Account > Deauthorize Sessions.":
        "Puedes cerrar la sesión de todos los dispositivos desde la bóveda web ( {{url}} ), en Ajustes > Mi cuenta > Desautorizar sesiones.",
    "You can deauthorize all devices that have access to your account from the":
        "Puedes cerrar la sesión de todos los dispositivos desde la",
    "under Settings > My Account > Deauthorize Sessions.":
        "en Ajustes > Mi cuenta > Desautorizar sesiones.",
    "Two-Step Login Recovered From {{ip}}":
        "Inicio de sesión en dos pasos desactivado desde {{ip}}",
    "Two-step login on your account has been disabled by using the account's recovery code.":
        "El inicio de sesión en dos pasos de tu cuenta se desactivó usando el código de recuperación.",
    "If you did not perform this action, you should immediately take steps to secure your account.":
        "Si no fuiste tú, toma medidas de inmediato para proteger tu cuenta.",

    # --- invitaciones a organizaciones
    "Invitation to {{{org_name}}} accepted": "Invitación a {{{org_name}}} aceptada",
    "This email is to notify you that {{email}} has accepted your invitation to join {{org_name}}.":
        "Te avisamos que {{email}} aceptó tu invitación para unirse a {{org_name}}.",
    "This email is to notify you that {{email}} has accepted your invitation to join <b>{{org_name}}</b>.":
        "Te avisamos que {{email}} aceptó tu invitación para unirse a <b>{{org_name}}</b>.",
    "Please log in via {{url}} to the vaultwarden server and confirm them from the organization management page.":
        "Entra a {{url}} y confírmalo desde la página de administración de la organización.",
    "Please": "Por favor",
    "log in": "inicia sesión",
    "to the vaultwarden server and confirm them from the organization management page.":
        "y confírmalo desde la página de administración de la organización.",
    "If you do not wish to confirm this user, you can also remove them from the organization on the same page.":
        "Si no deseas confirmarlo, puedes quitarlo de la organización en esa misma página.",
    "Invitation to {{{org_name}}} confirmed": "Invitación a {{{org_name}}} confirmada",
    "This email is to notify you that you have been confirmed as a user of {{org_name}}.":
        "Te avisamos que fuiste confirmado como usuario de {{org_name}}.",
    "This email is to notify you that you have been confirmed as a user of <b>{{org_name}}</b>.":
        "Te avisamos que fuiste confirmado como usuario de <b>{{org_name}}</b>.",
    "Any collections and logins being shared with you by this organization will now appear in your Vaultwarden vault at {{url}}.":
        "Las colecciones y accesos que esta organización comparta contigo aparecerán en tu bóveda de " + MARCA + " en {{url}}.",
    "Any collections and logins being shared with you by this organization will now appear in your Vaultwarden vault.":
        "Las colecciones y accesos que esta organización comparta contigo aparecerán en tu bóveda de " + MARCA + ".",
    "Log in": "Iniciar sesión",
    "Join {{{org_name}}}": "Te invitaron a {{{org_name}}}",
    "You have been invited to join the *{{org_name}}* organization.":
        "Te invitaron a unirte a *{{org_name}}*.",
    "You have been invited to join the <b>{{org_name}}</b> organization.":
        "Te invitaron a unirte a <b>{{org_name}}</b>.",
    "Click here to join: {{{url}}}": "Haz clic aquí para aceptar: {{{url}}}",
    "If you do not wish to join this organization, you can safely ignore this email.":
        "Si no deseas unirte, puedes ignorar este correo.",
    "Join Organization Now": "Aceptar invitación",
    "Your access to {{{org_name}}} has been revoked.": "Se revocó tu acceso a {{{org_name}}}.",
    "Your access to {{{org_name}}} has been revoked": "Se revocó tu acceso a {{{org_name}}}",
    "Your user account has been removed from the *{{org_name}}* organization because you do not have two-step login configured.":
        "Tu cuenta fue retirada de la organización *{{org_name}}* porque no tienes configurado el inicio de sesión en dos pasos.",
    "Your user account has been removed from the <b>{{org_name}}</b> organization because you do not have two-step login configured.":
        "Tu cuenta fue retirada de la organización <b>{{org_name}}</b> porque no tienes configurado el inicio de sesión en dos pasos.",
    "Before you can re-join this organization you need to set up two-step login on your user account.":
        "Para volver a unirte a esta organización necesitas activar el inicio de sesión en dos pasos en tu cuenta.",
    "You can enable two-step login in your account settings.":
        "Puedes activarlo en los ajustes de tu cuenta.",
    "Your access to the *{{org_name}}* organization has been revoked because you are a part of another organization. The {{org_name}} organization has enabled a policy that prevents users from being a part of multiple organizations. Before your access can be restored you need to leave all other organizations or join with a different account.":
        "Se revocó tu acceso a la organización *{{org_name}}* porque perteneces a otra organización. {{org_name}} activó una política que impide pertenecer a varias organizaciones. Para recuperar el acceso debes salir de las demás organizaciones o unirte con otra cuenta.",
    "Your access to the <b>{{org_name}}</b> organization has been revoked because you are a part of another organization. The {{org_name}} organization has enabled a policy that prevents users from being a part of multiple organizations. Before your access can be restored you need to leave all other organizations or join with a different account.":
        "Se revocó tu acceso a la organización <b>{{org_name}}</b> porque perteneces a otra organización. {{org_name}} activó una política que impide pertenecer a varias organizaciones. Para recuperar el acceso debes salir de las demás organizaciones o unirte con otra cuenta.",

    # --- códigos de verificación
    "Your Vaultwarden Verification Code": "Tu código de verificación de " + MARCA,
    "Your email verification code is: {{token}}": "Tu código de verificación es: {{token}}",
    "Your email verification code is: <b>{{token}}</b>": "Tu código de verificación es: <b>{{token}}</b>",
    "Use this code to complete the protected action in Vaultwarden.":
        "Usa este código para completar la acción protegida en " + MARCA + ".",
    "Vaultwarden Login Verification Code": "Código para iniciar sesión en " + MARCA,
    "Your two-step verification code is: {{token}}":
        "Tu código de verificación en dos pasos es: {{token}}",
    "Your two-step verification code is: <b>{{token}}</b>":
        "Tu código de verificación en dos pasos es: <b>{{token}}</b>",
    "Use this code to complete logging in with Vaultwarden.":
        "Usa este código para terminar de iniciar sesión en " + MARCA + ".",

    # --- pista de contraseña
    "Your master password hint": "La pista de tu contraseña maestra",
    "You (or someone) recently requested your master password hint. Unfortunately, your account does not have a master password hint.":
        "Tú (o alguien más) solicitó la pista de tu contraseña maestra. Tu cuenta no tiene una pista registrada.",
    "If you cannot remember your master password, there is no way to recover your data. The only option to gain access to your account again is to delete the account ( {{url}}/#/recover-delete ) so that you can register again and start over. All data associated with your account will be deleted.":
        "Si no recuerdas tu contraseña maestra, no hay forma de recuperar tus datos. La única opción para volver a usar tu cuenta es eliminarla ( {{url}}/#/recover-delete ) y registrarte de nuevo desde cero. Se borrarán todos los datos de la cuenta.",
    "If you did not request your master password hint you can safely ignore this email.":
        "Si no solicitaste la pista de tu contraseña maestra, puedes ignorar este correo.",
    "Sorry, you have no password hint...": "Tu cuenta no tiene pista de contraseña.",
    "If you cannot remember your master password, there is no way to recover your data. The only option to gain access to your account again is to":
        "Si no recuerdas tu contraseña maestra, no hay forma de recuperar tus datos. La única opción para volver a usar tu cuenta es",
    "delete the account": "eliminar la cuenta",
    "so that you can register again and start over. All data associated with your account will be deleted.":
        "y registrarte de nuevo desde cero. Se borrarán todos los datos de la cuenta.",
    "You (or someone) recently requested your master password hint.":
        "Tú (o alguien más) solicitó la pista de tu contraseña maestra.",
    "Your hint is: *{{hint}}*": "Tu pista es: *{{hint}}*",
    'Your hint is: "{{hint}}"': 'Tu pista es: "{{hint}}"',
    "Log in to the web vault: {{url}}": "Entra a la bóveda web: {{url}}",
    "Log in:": "Iniciar sesión:",
    "Web Vault": "Bóveda web",

    # --- verificación de correo y bienvenida
    "Verify Your Email": "Verifica tu correo electrónico",
    "Verify this email address to finish creating your account by clicking the link below.":
        "Verifica este correo para terminar de crear tu cuenta haciendo clic en el siguiente enlace.",
    "Verify Email Address Now: {{{url}}}": "Verificar mi correo: {{{url}}}",
    "Verify Email Address Now: {{url}}/#/verify-email/?userId={{user_id}}&token={{token}}":
        "Verificar mi correo: {{url}}/#/verify-email/?userId={{user_id}}&token={{token}}",
    "If you did not request to verify your account, you can safely ignore this email.":
        "Si no solicitaste verificar tu cuenta, puedes ignorar este correo.",
    "Verify Email Address Now": "Verificar mi correo",
    "Verify this email address for your account by clicking the link below.":
        "Verifica el correo de tu cuenta haciendo clic en el siguiente enlace.",
    "Welcome": "Te damos la bienvenida",
    "Thank you for creating an account at {{url}}. You may now log in with your new account.":
        "Gracias por crear tu cuenta en {{url}}. Ya puedes iniciar sesión.",
    "If you did not request to create an account, you can safely ignore this email.":
        "Si no solicitaste crear una cuenta, puedes ignorar este correo.",
    "Thank you for creating an account at": "Gracias por crear tu cuenta en",
    ". You may now log in with your new account.": ". Ya puedes iniciar sesión.",
    "Thank you for creating an account at {{url}}. Before you can login with your new account, you must verify this email address by clicking the link below.":
        "Gracias por crear tu cuenta en {{url}}. Antes de iniciar sesión debes verificar este correo haciendo clic en el siguiente enlace.",
    ". Before you can login with your new account, you must verify this email address by clicking the link below.":
        ". Antes de iniciar sesión debes verificar este correo haciendo clic en el siguiente enlace.",

    # --- varios
    "Vaultwarden SMTP Test": "Prueba de correo de " + MARCA,
    "This is a test email to verify the SMTP configuration for {{url}}.":
        "Este es un correo de prueba para verificar la configuración de envío de {{url}}.",
    "This is a test email to verify the SMTP configuration for":
        "Este es un correo de prueba para verificar la configuración de envío de",
    "When you can read this email it is probably configured correctly.":
        "Si puedes leerlo, el envío está bien configurado.",
    "Your Email Changed": "Tu correo cambió",
    "Your email was changed in your SSO Provider. Please update your email in Account Settings ({{url}}).":
        "Tu correo cambió en tu proveedor de inicio de sesión único. Actualízalo en los ajustes de tu cuenta ({{url}}).",
    "Your email was changed in your SSO Provider. Please update your email in":
        "Tu correo cambió en tu proveedor de inicio de sesión único. Actualízalo en los",
    "Account Settings": "ajustes de tu cuenta",
}


def patron(segmento):
    """Expresión regular que encuentra el segmento sin importar saltos de línea ni atributos de <b>."""
    partes = re.split(r"(<b>|\s+)", segmento)
    exp = "".join(r"(<b[^>]*>)" if p == "<b>" else r"\s+" if p.isspace() else re.escape(p)
                  for p in partes if p)
    # Solo texto completo: no dentro de otra palabra ni de un bloque {{ }}
    return re.compile(r"(?<![A-Za-z{])" + exp + r"(?![A-Za-z}])")


def traducir(texto, html):
    for original in sorted(TRADUCCIONES, key=len, reverse=True):
        destino = TRADUCCIONES[original]

        def sustituir(m, destino=destino):
            etiquetas = iter(m.groups())
            return re.sub(r"<b>", lambda _: next(etiquetas), destino)

        texto = patron(original).sub(sustituir, texto)
    return texto


def texto_visible(contenido, html):
    """Líneas de texto que vería el destinatario (para detectar inglés sin traducir)."""
    contenido = re.sub(r"\{\{>[^}]*\}\}", "", contenido).replace(SEPARADOR, "\n")
    if html:
        contenido = re.sub(r"<[^>]+>", "\n", contenido, flags=re.S)
    return [re.sub(r"\s+", " ", l).strip() for l in contenido.splitlines()]


INGLES = re.compile(r"\b(the|your|you|has|have|this|with|from|and|to|please|click|log in|account|"
                    r"email|vault|password|verify|welcome|invitation|organization)\b", re.I)


def descargar_originales(version, destino):
    """Baja src/static/templates/{email,admin} del código de Vaultwarden de esa versión."""
    url = f"https://codeload.github.com/dani-garcia/vaultwarden/tar.gz/refs/tags/{version}"
    with urllib.request.urlopen(url, timeout=120) as r:
        datos = r.read()
    temporal = destino.with_name(destino.name + ".tmp")
    if temporal.exists():
        shutil.rmtree(temporal)
    with tarfile.open(fileobj=io.BytesIO(datos), mode="r:gz") as tar:
        for miembro in tar.getmembers():
            m = re.search(r"/src/static/templates/(email|admin)/([A-Za-z0-9_.]+\.hbs)$", miembro.name)
            if not m or not miembro.isfile():
                continue
            salida = temporal / m.group(1) / m.group(2)
            salida.parent.mkdir(parents=True, exist_ok=True)
            salida.write_bytes(tar.extractfile(miembro).read())
    if not (temporal / "email" / "send_org_invite.hbs").exists() or not (temporal / "admin" / "base.hbs").exists():
        sys.exit(f"ERROR: la descarga de la versión {version} no trae las plantillas esperadas")
    temporal.rename(destino)


def construir_correos(origen, destino):
    pendientes = []
    archivos = sorted(p for p in origen.glob("*.hbs") if p.name not in PROPIOS)
    for ruta in archivos:
        html = ruta.name.endswith(".html.hbs")
        original = ruta.read_text(encoding="utf-8")
        asunto, cuerpo = original.split(SEPARADOR, 1)
        asunto = TRADUCCIONES.get(asunto.strip(), asunto.strip())
        traducido = asunto + "\n" + SEPARADOR + traducir(cuerpo, html)
        traducido = traducido.replace(COLOR_BOTON_ORIGINAL, COLOR_BOTON)
        (destino / ruta.name).write_text(traducido, encoding="utf-8")
        for linea in texto_visible(traducido, html):
            sin_variables = re.sub(r"\{\{.*?\}\}+", "", linea)
            sin_variables = re.sub(r"\S*[/#?&=]\S*", "", sin_variables)  # restos de enlaces
            if INGLES.search(sin_variables) and not re.search(r"[áéíóúñ¿¡]|\b(de|la|el|tu|en|que|para)\b", sin_variables):
                pendientes.append(f"{ruta.name}: {linea}")
    for nombre in PROPIOS:
        shutil.copyfile(BRANDING / "templates" / "email" / nombre, destino / nombre)
    return len(archivos), pendientes


def construir_admin(origen, destino):
    """Página base del panel /admin: ícono de pestaña, título y nombre de la marca."""
    html = (origen / "base.hbs").read_text(encoding="utf-8")
    cambios = (
        ('{{urlpath}}/vw_static/vaultwarden-favicon.png', '{{urlpath}}/images/favicon-32x32.png'),
        ('<title>Vaultwarden Admin Panel</title>', f'<title>{MARCA} - Administración</title>'),
        ('<img class="vaultwarden-icon" src="{{urlpath}}/vw_static/vaultwarden-icon.png" alt="V">aultwarden Admin</a>',
         f'<img src="{{{{urlpath}}}}/images/emblema.png" alt="" style="height: 26px; margin-right: 10px;">{MARCA} · Admin</a>'),
    )
    for viejo, nuevo in cambios:
        if html.count(viejo) != 1:
            sys.exit(f"ERROR: admin/base.hbs cambió en esta versión; no se encontró: {viejo}")
        html = html.replace(viejo, nuevo)
    (destino / "base.hbs").write_text(html, encoding="utf-8")


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        sys.exit(__doc__)
    version = sys.argv[1]
    originales = BRANDING / "originales" / version
    if not originales.is_dir():
        originales.parent.mkdir(parents=True, exist_ok=True)
        descargar_originales(version, originales)

    final = BASE / "plantillas" / version
    temporal = BASE / "plantillas" / f".{version}.tmp"
    if temporal.exists():
        shutil.rmtree(temporal)
    for sub in ("email", "admin"):
        (temporal / sub).mkdir(parents=True)

    total, pendientes = construir_correos(originales / "email", temporal / "email")
    construir_admin(originales / "admin", temporal / "admin")
    shutil.copytree(BRANDING / "templates" / "scss", temporal / "scss")

    if pendientes:
        shutil.rmtree(temporal)
        print(f"ERROR: {len(pendientes)} textos de correo quedarían en inglés. Agrégalos a TRADUCCIONES:")
        for p in pendientes:
            print("  " + p)
        sys.exit(1)

    # Se copia dentro de la carpeta existente para no romper el montaje de bóvedas en ejecución
    final.mkdir(parents=True, exist_ok=True)
    shutil.copytree(temporal, final, dirs_exist_ok=True)
    shutil.rmtree(temporal)
    for ruta in [final, *final.rglob("*")]:
        ruta.chmod(0o755 if ruta.is_dir() else 0o644)
    print(f"Plantillas listas en {final} ({total} correos traducidos)")


if __name__ == "__main__":
    main()
