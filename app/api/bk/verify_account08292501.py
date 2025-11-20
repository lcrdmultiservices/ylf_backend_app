from fastapi import APIRouter, Depends, HTTPException, Request, Response
# --- NUEVO: Importar JSONResponse ---
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone, timedelta

# Importaciones de nuestro proyecto
from app.db.database import get_db, get_mongo_db 
from app.utils.mongo_logger import log_error
from app.utils.otp_handler import verify_otp

router = APIRouter()

class VerifyRequest(BaseModel):
    user_id: int
    otp_code: str
     context: str
     
@router.post("/verify-account")
def verify_account(data: VerifyRequest, request: Request, response: Response, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db)):
    """
    Verifica un código OTP para la activación de la cuenta usando la lógica centralizada.
    """
    if mongo_db is None:
        log_error(mongo_db, request.url.path, "POST", "MongoDB connection not available.", data.dict())
        raise HTTPException(status_code=503, detail="error_db_connection")

    try:
        # 1. Obtener el email del usuario desde la base de datos SQL
        email_query = text("""
            SELECT email FROM accounts 
            WHERE idaccounts = (SELECT accounts_idaccounts FROM users_has_accounts WHERE users_idusers = :user_id AND `default` = 1)
        """)
        user_account = db.execute(email_query, {"user_id": data.user_id}).first()

        if not user_account:
            # Este es un error inesperado, por lo que una excepción es apropiada.
            raise HTTPException(status_code=404, detail="error_user_not_found")
        
        user_email = user_account[0]

        # 2. Verificar el OTP usando la función centralizada
        is_valid = verify_otp(
            mongo_db=mongo_db,
            email=user_email,
            otp_code=data.otp_code,
            otp_context="ACCOUNT_REGISTRATION",
            delete_on_verify=True
        )

        # --- CORRECCIÓN CLAVE ---
        # 3. Si el OTP no es válido, devolver una respuesta de error JSON controlada.
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "detail": "error_invalid_otp"}
            )

        # 4. Si el OTP es válido, activar la cuenta en la base de datos
        db.execute(text("UPDATE person SET status = 'active' WHERE idperson = :user_id"), {"user_id": data.user_id})
        db.execute(text("UPDATE users SET verified = 1 WHERE idusers = :user_id"), {"user_id": data.user_id})
        db.execute(text("UPDATE accounts SET email_verified = 1 WHERE idaccounts IN (SELECT accounts_idaccounts FROM users_has_accounts WHERE users_idusers = :user_id)"), {"user_id": data.user_id})
        db.commit()
        
        # 5. Devolver éxito
        session_token = f"simulated_jwt_token_for_user_{data.user_id}"
        print(f"Cuenta para user_id {data.user_id} verificada y activada exitosamente.")

        return {
            "status": "success",
            "message": "Account verified successfully.",
            "token": session_token
        }

    except Exception as e:
        db.rollback()
        log_error(mongo_db=mongo_db, endpoint=request.url.path, method="POST", error=e, request_payload=data.dict())
        raise HTTPException(status_code=500, detail="error_server_issue")
