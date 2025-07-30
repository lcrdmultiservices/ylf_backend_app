from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

# Importaciones de nuestro proyecto
from app.db.database import get_db, get_mongo_db
from app.utils.mongo_logger import log_error
from app.utils.mailgun_client import send_verification_email
# --- NUEVO: Importar el manejador de OTP centralizado ---
from app.utils.otp_handler import generate_and_store_otp

router = APIRouter()

class ResendRequest(BaseModel):
    user_id: int
    language: str = Field('en', description="Idioma para el correo (en, es, pt)")
    otp_context: str = Field('ACCOUNT_REGISTRATION', description="Contexto de la solicitud de OTP")

@router.post("/resend-verification-code")
def resend_otp(data: ResendRequest, request: Request, response: Response, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db)):
    """
    Genera y reenvía un nuevo código OTP usando la lógica centralizada.
    """
    if mongo_db is None or db is None:
        raise HTTPException(status_code=503, detail="error_db_connection")

    try:
        # 1. Obtener datos del usuario
        query = text("""
            SELECT p.email, p.first_name, u.verified 
            FROM users u 
            JOIN person p ON u.person_idperson = p.idperson 
            WHERE u.idusers = :user_id
        """)
        result = db.execute(query, {"user_id": data.user_id}).first()

        if not result:
            raise HTTPException(status_code=404, detail="error_user_not_found")

        user_email, user_first_name, is_verified = result

        if is_verified:
            raise HTTPException(status_code=400, detail="error_account_already_verified")

        # --- LÓGICA REFACTORIZADA ---
        # 2. Generar y guardar el nuevo OTP usando el manejador central
        new_otp_code = generate_and_store_otp(
            mongo_db=mongo_db,
            user_id=data.user_id,
            email=user_email,
            otp_context=data.otp_context
        )

        if not new_otp_code:
            raise HTTPException(status_code=500, detail="error_otp_generation_failed")

        # 3. Enviar el correo
        email_sent = send_verification_email(
            email_to=user_email,
            otp_code=new_otp_code,
            first_name=user_first_name,
            language=data.language,
            email_type='verification_otp' # Especificar el tipo de correo
        )

        if not email_sent:
            raise HTTPException(status_code=500, detail="error_email_send_failed")

        return {"status": "success", "message": "A new verification code has been sent."}

    except HTTPException as http_exc:
        # Re-lanzar excepciones HTTP para que FastAPI las maneje correctamente
        raise http_exc
    except Exception as e:
        log_error(mongo_db=mongo_db, endpoint=request.url.path, method="POST", error=e, request_payload=data.dict())
        raise HTTPException(status_code=500, detail="error_server_issue")
