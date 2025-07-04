import requests

MAILGUN_DOMAIN = "sandboxXXXXXXX.mailgun.org"  # Reemplaza con tu dominio Mailgun
MAILGUN_API_KEY = "key-XXXXXXXXXXXXXXXXXXXX"   # Reemplaza con tu API Key
SENDER_EMAIL = f"noreply@{MAILGUN_DOMAIN}"

def send_verification_email(to_email: str, verification_link: str):
    try:
        response = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API_KEY),
            data={
                "from": f"YourLostAndFound <{SENDER_EMAIL}>",
                "to": [to_email],
                "subject": "Verify your email",
                "text": f"Please verify your email by clicking the following link: {verification_link}"
            }
        )
        response.raise_for_status()
        return {"status": "sent", "code": 200}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "code": 500, "detail": str(e)}