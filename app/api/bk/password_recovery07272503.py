from fastapi import APIRouter, Depends, HTTPException
# --- NUEVO: Importar JSONResponse ---
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, constr
from sqlalchemy.orm import Session
from sqlalchemy import text
import bcrypt

# Importaciones de nuestro proyecto
from app.db.database import get_db, get_mongo_db
from app.utils.mailgun_client import send_verification_email
from app.utils.otp_handler import generate_and_store_otp, verify_otp

router = APIRouter(
    prefix="/password",
    tags=["Password Recovery"]
)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: constr(min_length=6, max_length=6)

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: constr(min_length=6, max_length=6)
    new_password: str

@router.post("/forgot", status_code=200)
async def request_password_reset(data: ForgotPasswordRequest, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db)):
    query = text("SELECT u.idusers, p.first_name FROM users u JOIN accounts a ON u.idusers = (SELECT uha.users_idusers FROM users_has_accounts uha WHERE uha.accounts_idaccounts = a.idaccounts) JOIN person p ON u.person_idperson = p.idperson WHERE a.email = :email AND a.authentication_type_idauthentication_type = 1")
    user_data = db.execute(query, {"email": data.email}).first()

    if user_data:
        otp_code = generate_and_store_otp(mongo_db=mongo_db, user_id=user_data.idusers, email=data.email, otp_context="PASSWORD_RESET", lifespan_minutes=5)
        if otp_code:
            send_verification_email(email_to=data.email, otp_code=otp_code, first_name=user_data.first_name, language='es', email_type='password_reset')

    return {"detail": "If an account with that email exists, a recovery code has been sent."}

@router.post("/verify-otp", status_code=200)
async def check_otp_validity(data: VerifyOtpRequest, mongo_db = Depends(get_mongo_db)):
    is_valid = verify_otp(mongo_db=mongo_db, email=data.email, otp_code=data.otp, otp_context="PASSWORD_RESET")

    # --- CORRECCIÓN CLAVE ---
    if not is_valid:
        return JSONResponse(status_code=400, content={"status": "error", "detail": "error_invalid_otp"})

    return {"status": "success", "detail": "OTP is valid."}

@router.post("/reset", status_code=200)
async def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db)):
    is_valid = verify_otp(mongo_db=mongo_db, email=data.email, otp_code=data.otp, otp_context="PASSWORD_RESET", delete_on_verify=True)

    # --- CORRECCIÓN CLAVE ---
    if not is_valid:
        return JSONResponse(status_code=400, content={"status": "error", "detail": "error_invalid_otp"})

    hashed_password = bcrypt.hashpw(data.new_password.encode('utf-8'), bcrypt.gensalt())
    update_query = text("UPDATE accounts SET hash_password = :new_password WHERE email = :email AND authentication_type_idauthentication_type = 1")
    
    try:
        result = db.execute(update_query, {"new_password": hashed_password.decode('utf-8'), "email": data.email})
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="error_user_not_found")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="error_database_update_failed")

    return {"detail": "Password has been reset successfully."}
