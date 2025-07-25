# En: app/api/endpoints/resend_otp.py (o la ruta que corresponda)

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import random

# --- Importaciones de tu proyecto ---
from app.db.database import get_db, get_mongo_db
from app.utils.mongo_logger import log_error
# Importamos el cliente de correo que ya tienes
from app.utils.mailgun_client import send_verification_email 
# Modelo de la base de datos de MySQL para obtener el nombre del usuario
from app.models.user import User  # Asegúrate de que la ruta de importación sea correcta

router = APIRouter()

class ResendRequest(BaseModel):
    user_id: int
    language: str = Field('en', description="Idioma para el correo (en, es, pt)")

@router.post("/resend-verification-code")
def resend_otp(data: ResendRequest, request: Request, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db)):
    """
    Genera un nuevo código OTP, lo guarda en MongoDB y lo envía al usuario.
    """
    if mongo_db is None or db is None:
        raise HTTPException(status_code=500, detail="error_server_issue")

    try:
        # 1. Buscar al usuario en MySQL para obtener su email y nombre
        user = db.query(User).filter(User.idusers == data.user_id).first()
        if not user:
            log_error(mongo_db, request.url.path, "POST", f"User not found with id: {data.user_id}", data.dict())
            raise HTTPException(status_code=404, detail="error_user_not_found")

        if user.verified:
            raise HTTPException(status_code=400, detail="error_account_already_verified")

        # 2. Generar un nuevo código OTP y su fecha de expiración
        new_otp_code = str(random.randint(100000, 999999))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10) # Nueva expiración de 10 min

        otp_collection = mongo_db.otp_codes

        # 3. Invalidar códigos OTP anteriores para este usuario (opcional pero recomendado)
        otp_collection.update_many(
            {"user_id": data.user_id, "used": False},
            {"$set": {"used": True, "notes": "Invalidated by new code request"}}
        )

        # 4. Insertar el nuevo código OTP en MongoDB
        otp_collection.insert_one({
            "user_id": data.user_id,
            "otp_code": new_otp_code,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "used": False,
            "notes": ""
        })
        
        # 5. Enviar el correo usando la función reutilizable de mailgun_client.py
        email_sent = send_verification_email(
            email_to=user.email,
            otp_code=new_otp_code,
            first_name=user.first_name, # Asumiendo que tienes un campo first_name
            language=data.language
        )

        if not email_sent:
            log_error(mongo_db, request.url.path, "POST", "Mailgun failed to send email.", data.dict())
            # La transacción es exitosa aunque el email falle, el usuario puede reintentar
            raise HTTPException(status_code=500, detail="error_email_send_failed")

        return {
            "status": "success",
            "message": "A new verification code has been sent."
        }

    except HTTPException as http_exc:
        # Re-lanzar las excepciones HTTP que generamos intencionalmente
        raise http_exc
    except Exception as e:
        # Registrar cualquier otro error inesperado
        log_error(mongo_db, request.url.path, "POST", str(e), data.dict())
        raise HTTPException(status_code=500, detail="error_server_issue")