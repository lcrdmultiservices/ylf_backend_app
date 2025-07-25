from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone

from app.db.database import get_db, get_mongo_db 
from app.utils.mongo_logger import log_error

router = APIRouter()

class VerifyRequest(BaseModel):
    user_id: int
    otp_code: str

@router.post("/verify-account")
def verify_account(data: VerifyRequest, request: Request, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db)):
    """
    Verifica un código OTP, activa la cuenta del usuario y crea una sesión.
    """
    if mongo_db is None:
        log_error(mongo_db, request.url.path, "POST", "MongoDB connection not available.", data.dict())
        raise HTTPException(status_code=503, detail="error_db_connection")

    try:
        otp_collection = mongo_db.otp_codes
        
        # 1. Buscar el OTP en MongoDB
        otp_document = otp_collection.find_one({
            "user_id": data.user_id,
            "otp_code": data.otp_code,
            "used": False,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })

        if not otp_document:
            # El código es inválido, ha expirado o ya fue usado.
            # Esto ahora devolverá un error 400 claro al frontend.
            raise HTTPException(status_code=400, detail="error_invalid_otp")

        # 2. Marcar el OTP como usado en MongoDB
        otp_collection.update_one(
            {"_id": otp_document["_id"]},
            {"$set": {"used": True}}
        )

        # 3. Activar la cuenta en la base de datos MySQL
        db.execute(text("UPDATE person SET status = 'active' WHERE idperson = :user_id"), {"user_id": data.user_id})
        db.execute(text("UPDATE users SET verified = 1 WHERE idusers = :user_id"), {"user_id": data.user_id})
        db.execute(text("UPDATE accounts SET email_verified = 1 WHERE idaccounts IN (SELECT accounts_idaccounts FROM users_has_accounts WHERE users_idusers = :user_id)"), {"user_id": data.user_id})
        db.commit()
        
        # 4. (Simulación) Generar y devolver un token de sesión
        session_token = f"simulated_jwt_token_for_user_{data.user_id}"

        print(f"Cuenta para user_id {data.user_id} verificada y activada exitosamente.")

        return {
            "status": "success",
            "message": "Account verified successfully.",
            "token": session_token
        }

    except HTTPException as http_exc:
        # CORRECCIÓN: Re-lanzar las excepciones HTTP que generamos intencionalmente.
        # Esto asegura que los errores 400, 404, etc., lleguen al frontend como tales.
        raise http_exc
    except Exception as e:
        # CORRECCIÓN: Este bloque ahora solo capturará errores inesperados del servidor.
        log_error(mongo_db=mongo_db, endpoint=request.url.path, method="POST", error=str(e), request_payload=data.dict())
        raise HTTPException(status_code=500, detail="error_server_issue")
