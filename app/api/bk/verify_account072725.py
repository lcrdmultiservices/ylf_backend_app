from fastapi import APIRouter, Depends, HTTPException, Request, Response
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
def verify_account(data: VerifyRequest, request: Request, response: Response, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db)):
    """
    Verifica un código OTP. Devuelve siempre 200 OK, pero con un cuerpo JSON 
    que indica el estado de la operación ('success' o 'error').
    """
    if mongo_db is None:
        # Aquí la llamada es correcta porque estamos dentro del mismo archivo
        log_error(mongo_db, request.url.path, "POST", "MongoDB connection not available.", data.dict())
        response.status_code = 503
        return {"status": "error", "detail": "error_db_connection"}

    # 1. Buscar el OTP en MongoDB.
    otp_collection = mongo_db.otp_codes
    otp_document = otp_collection.find_one({
        "user_id": data.user_id,
        "otp_code": data.otp_code,
        "used": False,
        "expires_at": {"$gt": datetime.now(timezone.utc)}
    })

    # 2. Si el OTP no es válido, devolver una respuesta de error controlada.
    if not otp_document:
        response.status_code = 400
        return {"status": "error", "detail": "error_invalid_otp"}

    # 3. Si el OTP es válido, proceder y devolver éxito.
    try:
        otp_collection.update_one({"_id": otp_document["_id"]}, {"$set": {"used": True}})
        
        db.execute(text("UPDATE person SET status = 'active' WHERE idperson = :user_id"), {"user_id": data.user_id})
        db.execute(text("UPDATE users SET verified = 1 WHERE idusers = :user_id"), {"user_id": data.user_id})
        db.execute(text("UPDATE accounts SET email_verified = 1 WHERE idaccounts IN (SELECT accounts_idaccounts FROM users_has_accounts WHERE users_idusers = :user_id)"), {"user_id": data.user_id})
        db.commit()
        
        session_token = f"simulated_jwt_token_for_user_{data.user_id}"
        print(f"Cuenta para user_id {data.user_id} verificada y activada exitosamente.")

        return {
            "status": "success",
            "message": "Account verified successfully.",
            "token": session_token
        }

    except Exception as e:
        # --- CORRECCIÓN CLAVE ---
        # Ahora pasamos el objeto 'mongo_db' a la función de logging.
        log_error(mongo_db=mongo_db, endpoint=request.url.path, method="POST", error=str(e), request_payload=data.dict())
        response.status_code = 500
        return {"status": "error", "detail": "error_server_issue"}
