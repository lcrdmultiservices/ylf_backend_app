from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text
import bcrypt

# Importaciones de nuestro proyecto
from app.db.database import get_db, get_mongo_db
from app.utils.mailgun_client import send_verification_email
# MODIFICADO: Ahora importamos desde el nuevo manejador de OTP
from app.utils.otp_handler import generate_and_store_otp

router = APIRouter()

class RegistrationRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    language: str = 'en'

@router.post("/register/local/personal")
async def register_local_personal_user(data: RegistrationRequest, request: Request, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db)):
    # 1. Verificar si el correo ya existe
    query = text("SELECT idaccounts FROM accounts WHERE email = :email")
    existing_user = db.execute(query, {"email": data.email}).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="error_email_exists")

    # 2. Hashear la contraseña
    hashed_password = bcrypt.hashpw(data.password.encode('utf-8'), bcrypt.gensalt())

    try:
        # 3. Crear registros en la base de datos (person, users, accounts, etc.)
        # (La lógica de la transacción de base de datos se mantiene igual)
        
        # Iniciar transacción
        person_query = text("""
            INSERT INTO person (first_name, last_name, status) 
            VALUES (:first_name, :last_name, 'pending_verification') RETURNING idperson
        """)
        person_result = db.execute(person_query, {"first_name": data.first_name, "last_name": data.last_name}).fetchone()
        id_person = person_result[0]

        user_query = text("""
            INSERT INTO users (person_idperson, verified, registration_date) 
            VALUES (:id_person, 0, NOW()) RETURNING idusers
        """)
        user_result = db.execute(user_query, {"id_person": id_person}).fetchone()
        id_user = user_result[0]

        account_query = text("""
            INSERT INTO accounts (email, hash_password, authentication_type_idauthentication_type, email_verified) 
            VALUES (:email, :password, 1, 0) RETURNING idaccounts
        """)
        account_result = db.execute(account_query, {"email": data.email, "password": hashed_password.decode('utf-8')}).fetchone()
        id_account = account_result[0]

        uha_query = text("""
            INSERT INTO users_has_accounts (users_idusers, accounts_idaccounts) 
            VALUES (:id_user, :id_account)
        """)
        db.execute(uha_query, {"id_user": id_user, "id_account": id_account})

        # 4. Generar y enviar OTP usando la función importada
        otp_code = generate_and_store_otp(
            mongo_db=mongo_db, 
            user_id=id_user, 
            email=data.email, 
            otp_context="LOGIN_VERIFICATION"
        )

        if otp_code:
            send_verification_email(
                email_to=data.email, 
                otp_code=otp_code, 
                first_name=data.first_name, 
                language=data.language
            )
            db.commit()
            return {"status": "success_pending_verification", "userId": id_user, "email": data.email}
        else:
            # Si el OTP falla, revertir la transacción
            db.rollback()
            raise HTTPException(status_code=500, detail="error_otp_generation_failed")

    except Exception as e:
        db.rollback()
        # Aquí podrías registrar el error con tu logger
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

# La función generate_and_store_otp ha sido movida a app/utils/otp_handler.py
