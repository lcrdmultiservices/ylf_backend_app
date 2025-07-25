from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone, timedelta
import random

from app.db.database import get_db, get_mongo_db
from app.utils.mongo_logger import log_error
from app.utils.mailgun_client import send_verification_email
from app.config import settings

router = APIRouter()

class ResendRequest(BaseModel):
    user_id: int
    language: str = Field('en', description="Idioma para el correo (en, es, pt)")
    otp_context: str = Field('ACCOUNT_REGISTRATION', description="Contexto de la solicitud de OTP")

@router.post("/resend-verification-code")
def resend_otp(data: ResendRequest, request: Request, response: Response, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db)):
    """
    Genera y reenvía un nuevo código OTP.
    """
    if mongo_db is None or db is None:
        response.status_code = 503
        return {"status": "error", "detail": "error_db_connection"}

    try:
        # --- CORRECCIÓN CLAVE EN LA CONSULTA SQL ---
        # Se ha cambiado 'u.email' por 'p.email' para que coincida con el esquema de la base de datos.
        query = text("""
            SELECT p.email, p.first_name, u.verified 
            FROM users u 
            JOIN person p ON u.person_idperson = p.idperson 
            WHERE u.idusers = :user_id
        """)
        result = db.execute(query, {"user_id": data.user_id}).first()

        if not result:
            log_error(mongo_db, request.url.path, "POST", f"User not found with id: {data.user_id}", data.dict())
            response.status_code = 404
            return {"status": "error", "detail": "error_user_not_found"}

        user_email = result.email
        user_first_name = result.first_name
        is_verified = result.verified

        if is_verified:
            response.status_code = 400
            return {"status": "error", "detail": "error_account_already_verified"}

        # Generar y guardar el nuevo OTP con su contexto
        new_otp_code = str(random.randint(100000, 999999))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRATION_MINUTES)
        
        otp_collection = mongo_db.otp_codes
        otp_collection.insert_one({
            "user_id": data.user_id,
            "email": user_email,
            "otp_code": new_otp_code,
            "otp_context": data.otp_context,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "used": False
        })
        
        # Enviar el correo
        email_sent = send_verification_email(
            email_to=user_email,
            otp_code=new_otp_code,
            first_name=user_first_name,
            language=data.language
        )

        if not email_sent:
            log_error(mongo_db, request.url.path, "POST", "Mailgun failed to send resend email.", data.dict())
            response.status_code = 500
            return {"status": "error", "detail": "error_email_send_failed"}

        return {"status": "success", "message": "A new verification code has been sent."}

    except Exception as e:
        log_error(mongo_db=mongo_db, endpoint=request.url.path, method="POST", error=e, request_payload=data.dict())
        response.status_code = 500
        return {"status": "error", "detail": "error_server_issue"}
