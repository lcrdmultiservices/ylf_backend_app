from fastapi import APIRouter, Depends, HTTPException, Request, Response
# --- NUEVO: Importar JSONResponse ---
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text
import bcrypt
import redis
import httpx
from datetime import timedelta
from typing import Optional

from app.db.database import get_db, get_mongo_db, get_redis_client
from app.utils.mongo_logger import log_error
from app.utils.mailgun_client import send_verification_email
from app.api.register_local_personal import generate_and_store_otp
from app.config import settings

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False
    hcaptcha_token: Optional[str] = None

# --- Rate Limiting con Redis (sin cambios) ---
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_TIMEFRAME = timedelta(minutes=15)

def check_rate_limit(redis_client: redis.Redis, email: str):
    if redis_client is None: return True
    key = f"login_attempts:{email}"
    attempts = redis_client.get(key)
    if attempts and int(attempts) >= LOGIN_ATTEMPT_LIMIT:
        raise HTTPException(status_code=429, detail="error_too_many_attempts")
    return True

def record_failed_attempt(redis_client: redis.Redis, email: str):
    if redis_client is None: return
    key = f"login_attempts:{email}"
    try:
        current_attempts = redis_client.incr(key)
        if current_attempts == 1:
            redis_client.expire(key, int(LOGIN_ATTEMPT_TIMEFRAME.total_seconds()))
    except redis.RedisError as e:
        print(f"Redis Error: Could not record failed login attempt for {email}. Error: {e}")

def clear_rate_limit(redis_client: redis.Redis, email: str):
    if redis_client is None: return
    key = f"login_attempts:{email}"
    redis_client.delete(key)


@router.post("/login/local")
async def login_local_user(data: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db), redis_client: redis.Redis = Depends(get_redis_client)):
    
    check_rate_limit(redis_client, data.email)

    if data.hcaptcha_token:
        try:
            async with httpx.AsyncClient() as client:
                hcaptcha_response = await client.post("https://api.hcaptcha.com/siteverify", data={'secret': settings.HCAPTCHA_SECRET_KEY, 'response': data.hcaptcha_token})
                if not hcaptcha_response.json().get("success"):
                    raise HTTPException(status_code=400, detail="error_captcha_failed")
        except Exception as e:
            raise HTTPException(status_code=500, detail="error_captcha_verification_failed")

    query = text("""
        SELECT u.idusers, a.hash_password, u.verified, p.first_name
        FROM accounts a
        JOIN users_has_accounts uha ON a.idaccounts = uha.accounts_idaccounts
        JOIN users u ON uha.users_idusers = u.idusers
        JOIN person p ON u.person_idperson = p.idperson
        WHERE a.email = :email AND a.authentication_type_idauthentication_type = 1
    """)
    user_data = db.execute(query, {"email": data.email}).first()

    # --- LÓGICA DE ERROR CORREGIDA Y DEFINITIVA ---
    # En lugar de lanzar una excepción, devolvemos una respuesta JSON directamente.
    # Esto evita que el error sea malinterpretado por otros manejadores.
    if not user_data or not bcrypt.checkpw(data.password.encode('utf-8'), user_data.hash_password.encode('utf-8')):
        record_failed_attempt(redis_client, data.email)
        return JSONResponse(
            status_code=401,
            content={"detail": "error_invalid_credentials"}
        )

    clear_rate_limit(redis_client, data.email)

    user_id = user_data.idusers
    is_verified = user_data.verified

    if not is_verified:
        otp_code = generate_and_store_otp(mongo_db, user_id=user_id, email=data.email, otp_context="LOGIN_VERIFICATION")
        
        if otp_code:
            send_verification_email(email_to=data.email, otp_code=otp_code, first_name=user_data.first_name, language='es')
            return {"status": "success_pending_verification", "userId": user_id, "email": data.email}
        else:
            raise HTTPException(status_code=500, detail="error_otp_generation_failed")

    session_token = f"simulated_jwt_token_for_user_{user_id}"
    
    if data.remember_me:
        response.set_cookie(key="session_token", value=session_token, max_age=172800, httponly=True, samesite='lax')
    else:
        response.set_cookie(key="session_token", value=session_token, httponly=True, samesite='lax')

    return {"status": "success", "token": session_token}
