import requests
import base64
import json
from app.config import settings
from app.utils.email_texts import email_content

# MODIFICADO: La función ahora acepta 'email_type' para seleccionar la plantilla de texto correcta.
def send_verification_email(email_to: str, otp_code: str, first_name: str, language: str = 'en', email_type: str = 'verification_otp') -> bool:
    """
    Envía un correo electrónico con un código OTP usando la API de Mailgun.
    La función ahora es genérica y puede enviar diferentes tipos de correos (verificación, reseteo de contraseña)
    basado en el parámetro 'email_type'.
    """
    if not settings.MAILGUN_API_KEY or not settings.MAILGUN_DOMAIN:
        print("ERROR: Las credenciales de Mailgun no están configuradas. No se puede enviar el correo.")
        return False

    if not hasattr(settings, 'FRONTEND_URL') or not settings.FRONTEND_URL:
        print("CRITICAL ERROR: La variable FRONTEND_URL no está configurada en el archivo de settings. No se puede generar el enlace de reporte.")
        report_link = "#"
    else:
        report_data = {"email": email_to, "topic": "otp_not_authorized"}
        report_json = json.dumps(report_data)
        report_base64 = base64.urlsafe_b64encode(report_json.encode()).decode()
        report_link = f"{settings.FRONTEND_URL}/help?report={report_base64}"

    # MODIFICADO: Selecciona dinámicamente el contenido del correo.
    # Si el 'email_type' no existe, usa 'verification_otp' como fallback seguro.
    texts = email_content.get(email_type, email_content.get("verification_otp", {}))
    
    # El resto de la lógica para obtener los textos es la misma.
    subject_template = texts.get("subject", {}).get(language, texts.get("subject", {}).get('en', 'Verification Code'))
    subject = subject_template.format(otp_code=otp_code)

    title = texts.get("title", {}).get(language, texts.get("title", {}).get('en', 'Verification'))
    greeting = texts.get("greeting", {}).get(language, texts.get("greeting", {}).get('en', 'Hi'))
    body = texts.get("body", {}).get(language, texts.get("body", {}).get('en', 'Here is your code.'))
    farewell = texts.get("farewell", {}).get(language, texts.get("farewell", {}).get('en', 'The team'))
    unsolicited_text_template = texts.get("unsolicited_link_text", {}).get(language, texts.get("unsolicited_link_text", {}).get('en', ''))
    
    unsolicited_text = unsolicited_text_template.format(link=report_link)

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; text-align: center; color: #333; padding: 20px;">
            <div style="max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 10px; padding: 20px;">
                <h2>{title}</h2>
                <p>{greeting} {first_name},</p>
                <p>{body}</p>
                <p style="font-size: 24px; font-weight: bold; letter-spacing: 5px; background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0;">{otp_code}</p>
                <p>{farewell},<br/>{settings.MAILGUN_FROM_NAME}</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;"/>
                <p style="font-size: 12px; color: #888;">{unsolicited_text}</p>
            </div>
        </body>
    </html>
    """

    try:
        response = requests.post(
            f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
            auth=("api", settings.MAILGUN_API_KEY),
            data={
                "from": f"{settings.MAILGUN_FROM_NAME} <{settings.MAILGUN_FROM_EMAIL}>",
                "to": [email_to],
                "subject": subject,
                "html": html_body
            }
        )
        response.raise_for_status()
        print(f"Correo de tipo '{email_type}' enviado exitosamente a {email_to} en '{language}'.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar correo de tipo '{email_type}' a {email_to}: {e}")
        return False
