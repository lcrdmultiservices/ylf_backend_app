from fastapi import APIRouter, Depends, HTTPException, Request, Response
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
from app.utils.otp_handler import generate_and_store_otp
from app.config import settings
# --- NUEVAS IMPORTACIONES ---
from app.utils.jwt_handler import create_access_token

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False
    hcaptcha_token: Optional[str] = None

LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_TIMEFRAME = timedelta(minutes=15)

# (Las funciones check_rate_limit, record_failed_attempt y clear_rate_limit permanecen igual)
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
    try:
        check_rate_limit(redis_client, data.email)
    except HTTPException as e:
        log_error(mongo_db, "/login/local", "POST", e, {"email": data.email}, {"client_host": request.client.host})
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

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

    if user_data and bcrypt.checkpw(data.password.encode('utf-8'), user_data.hash_password.encode('utf-8')):
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

        # --- LÓGICA DE CREACIÓN DE TOKEN JWT ---
        if data.remember_me:
            # Sesión larga (ej. 30 días) si el usuario marca "Recordarme"
            expires = timedelta(days=30)
            max_age = expires.total_seconds()
        else:
            # Sesión corta (ej. 2 horas) por defecto
            expires = timedelta(hours=2)
            max_age = None # La cookie expira cuando el navegador se cierra

        # Creamos el token con el ID de usuario y la duración
        # El 'sub' (subject) es la forma estándar de guardar el ID de usuario en un JWT
        token_data = {"sub": str(user_id)}
        access_token = create_access_token(data=token_data, expires_delta=expires)
        
        # Guardamos el token en la cookie
        response.set_cookie(
            key="session_token",
            value=access_token,
            max_age=max_age,
            httponly=True,
            samesite='lax',
            path='/'
        )

        return {"status": "success", "token": access_token}
    else:
        record_failed_attempt(redis_client, data.email)
        try:
            check_rate_limit(redis_client, data.email)
        except HTTPException as e:
            log_error(mongo_db, "/login/local", "POST", e, {"email": data.email}, {"client_host": request.client.host})
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
        
        return JSONResponse(
            status_code=401,
            content={"detail": "error_invalid_credentials"}
        )