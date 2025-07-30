import requests
from app.config import settings
# --- NUEVO: Importar el diccionario de textos ---
from app.utils.email_texts import email_content

def send_verification_email(email_to: str, otp_code: str, first_name: str, language: str = 'en') -> bool:
    """
    Envía un correo de verificación con un código OTP usando la API de Mailgun.
    Ahora es multilingüe.
    """
    if not settings.MAILGUN_API_KEY or not settings.MAILGUN_DOMAIN:
        print("ERROR: Las credenciales de Mailgun no están configuradas. No se puede enviar el correo.")
        return False

    # --- NUEVO: Seleccionar los textos según el idioma ---
    # Si el idioma no existe, se usa 'en' como fallback.
    texts = email_content.get("verification_otp", {})
    subject = texts.get("subject", {}).get(language, texts.get("subject", {}).get('en', "Verification Code"))
    title = texts.get("title", {}).get(language, texts.get("title", {}).get('en', "Verify Your Account"))
    greeting = texts.get("greeting", {}).get(language, texts.get("greeting", {}).get('en', "Hi"))
    body = texts.get("body", {}).get(language, texts.get("body", {}).get('en', "Your code is:"))
    farewell = texts.get("farewell", {}).get(language, texts.get("farewell", {}).get('en', "The team"))

    # --- NUEVO: Cuerpo del correo en HTML ---
    # Este HTML es simple, pero puedes expandirlo con estilos, tu logo, etc.
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; text-align: center; color: #333;">
            <h2>{title}</h2>
            <p>{greeting} {first_name},</p>
            <p>{body}</p>
            <p style="font-size: 24px; font-weight: bold; letter-spacing: 5px; background-color: #f0f0f0; padding: 10px; border-radius: 5px;">{otp_code}</p>
            <p>{farewell},<br/>{settings.MAILGUN_FROM_NAME}</p>
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
                # Se envía el cuerpo del correo directamente como HTML
                "html": html_body
            }
        )
        
        response.raise_for_status()
        print(f"Correo de verificación enviado exitosamente a {email_to} en '{language}'.")
        return True

    except requests.exceptions.RequestException as e:
        print(f"Error al enviar correo de verificación a {email_to}: {e}")
        return False


