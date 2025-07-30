from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text
import bcrypt

# Importar dependencias de DB y logging
from app.db.database import get_db, get_mongo_db 
from app.utils.mongo_logger import log_error

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

@router.post("/login/local")
def login_local_user(data: LoginRequest, request: Request, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db)):
    """
    Autentica a un usuario local con email y contraseña.
    """
    try:
        # 1. Buscar la cuenta por email para obtener el hash de la contraseña
        query = text("""
            SELECT idaccounts, hash_password, users_idusers 
            FROM accounts 
            JOIN users_has_accounts ON accounts.idaccounts = users_has_accounts.accounts_idaccounts
            WHERE email = :email
        """)
        account = db.execute(query, {"email": data.email}).fetchone()

        if not account:
            raise HTTPException(status_code=401, detail="error_invalid_credentials")

        # 2. Verificar la contraseña
        account_data = dict(account._mapping)
        if not verify_password(data.password, account_data['hash_password']):
            raise HTTPException(status_code=401, detail="error_invalid_credentials")

        # 3. (Simulación) Generar un token de sesión
        # En una aplicación real, aquí se generaría un token JWT (JSON Web Token)
        session_token = f"simulated_jwt_token_for_user_{account_data['users_idusers']}"

        # 4. Devolver una respuesta exitosa
        return {
            "status": "success", 
            "message": "Login successful", 
            "user_id": account_data['users_idusers'],
            "token": session_token 
        }

    except HTTPException as http_exc:
        # Re-lanzar excepciones HTTP para que FastAPI las maneje
        raise http_exc
    except Exception as e:
        # Registrar cualquier otro error inesperado en MongoDB
        log_error(
            mongo_db=mongo_db,
            endpoint=request.url.path,
            method="POST",
            error=e,
            request_payload={"email": data.email}, # No incluir la contraseña en los logs
            user_context={"client_ip": request.client.host if request.client else "N/A"}
        )
        raise HTTPException(status_code=500, detail="error_server_issue")
