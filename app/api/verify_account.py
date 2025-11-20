# en app/api/verify_account.py

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import timedelta

# Importaciones de nuestro proyecto
from app.db.database import get_db, get_mongo_db 
from app.utils.mongo_logger import log_error
from app.utils.otp_handler import verify_otp
# --- CORRECCIÓN 1: Importar el creador de tokens JWT ---
from app.utils.jwt_handler import create_access_token

router = APIRouter()

class VerifyRequest(BaseModel):
    user_id: int
    otp_code: str
    # --- CORRECCIÓN 2: Eliminar el espacio extra ---
    context: str
     
@router.post("/verify-account")
# --- CORRECCIÓN 3: Eliminar 'response: Response' de los parámetros ---
def verify_account(data: VerifyRequest, request: Request, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db)):
    """
    Verifica un código OTP, activa la cuenta E INICIA LA SESIÓN creando una cookie.
    """
    if mongo_db is None:
        raise HTTPException(status_code=503, detail="error_db_connection")

    try:
        email_query = text("SELECT email FROM accounts WHERE idaccounts = (SELECT accounts_idaccounts FROM users_has_accounts WHERE users_idusers = :user_id AND `default` = 1)")
        user_account = db.execute(email_query, {"user_id": data.user_id}).first()

        if not user_account:
            raise HTTPException(status_code=404, detail="error_user_not_found")
        
        user_email = user_account.email

        is_valid = verify_otp(
            mongo_db=mongo_db,
            email=user_email,
            otp_code=data.otp_code,
            otp_context=data.context,
            delete_on_verify=True
        )

        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "detail": "error_invalid_otp"}
            )

        # Si el OTP es válido, activar la cuenta en la base de datos
        db.execute(text("UPDATE users SET verified = 1 WHERE idusers = :user_id"), {"user_id": data.user_id})
        db.execute(text("UPDATE accounts SET email_verified = 1 WHERE idaccounts IN (SELECT accounts_idaccounts FROM users_has_accounts WHERE users_idusers = :user_id)"), {"user_id": data.user_id})
        db.commit()
        
        # LÓGICA DE INICIO DE SESIÓN COMPLETA Y CORRECTA
        expires = timedelta(hours=2)
        token_data = {"sub": str(data.user_id)}
        access_token = create_access_token(data=token_data, expires_delta=expires)
        
        response = JSONResponse(content={"status": "success", "token": access_token})
        
        response.set_cookie(
            key="session_token",
            value=access_token,
            httponly=True,
            samesite='lax',
            path='/'
        )
        
        print(f"Cuenta para user_id {data.user_id} verificada y SESIÓN INICIADA.")
        
        return response
        
    except Exception as e:
        db.rollback()
        log_error(mongo_db=mongo_db, endpoint=request.url.path, method="POST", error=e, request_payload=data.dict())
        raise HTTPException(status_code=500, detail="error_server_issue")