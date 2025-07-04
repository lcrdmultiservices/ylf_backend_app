from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import traceback
import requests
import os
import bcrypt # Usaremos bcrypt para hashear contraseñas de forma segura

# Importamos la dependencia get_db
from app.db.database import get_db

router = APIRouter()

# --- Modelos de Datos Pydantic ---
class RegisterLocalUser(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    birth_date: str  # Formato YYYY-MM-DD
    phone_number: str
    country_iso: str # Recibimos el código ISO2, ej: "US"
    password: str

# --- Lógica de Hashing de Contraseña ---
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

# --- Lógica de Envío de Correo ---
def send_verification_email(first_name: str, email: str, person_id: int):
    MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
    MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")
    MAILGUN_SENDER = os.getenv("MAILGUN_SENDER", f"noreply@{MAILGUN_DOMAIN}")
    
    if not (MAILGUN_API_KEY and MAILGUN_DOMAIN):
        print("WARN: Mailgun credentials not set. Skipping email.")
        return

    # TODO: Actualiza el dominio base cuando pases a producción
    verification_link = f"https://yourlostandfound.com/verify-email?token={person_id}" # Simplificado por ahora

    try:
        response = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API_KEY),
            data={
                "from": f"YourLostAndFound <{MAILGUN_SENDER}>",
                "to": [email],
                "subject": "Verify your email address",
                "text": f"Hello {first_name},\n\nPlease verify your email address by clicking this link:\n{verification_link}\n\nThank you!",
            },
        )
        if response.status_code != 200:
            # Loguear el error sin detener el flujo principal
            print(f"Mailgun error: {response.status_code} - {response.text}")
    except Exception as mail_error:
        print(f"Failed to send email: {str(mail_error)}")


@router.post("/register/local/personal")
def register_local_user(data: RegisterLocalUser, db: Session = Depends(get_db)):
    # Inicia la transacción. Si algo falla, se revierte todo.
    try:
        # 1. Verificar si el email ya existe en la tabla de cuentas
        existing_account = db.execute(text("SELECT idaccounts FROM accounts WHERE email = :email"), {"email": data.email}).fetchone()
        if existing_account:
            raise HTTPException(status_code=409, detail={"code": "REG_EMAIL_EXISTS", "msg": "An account with this email already exists."})

        # --- Inicia la creación de registros ---
        db.begin()

        # 2. Insertar persona
        person_query = text("""
            INSERT INTO person (first_name, last_name, email, dob, status)
            VALUES (:first_name, :last_name, :email, :dob, 'pending')
        """)
        db.execute(person_query, {
            "first_name": data.first_name, "last_name": data.last_name, 
            "email": data.email, "dob": data.birth_date
        })
        person_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        
        # 3. Insertar teléfono y asociarlo
        phone_query = text("INSERT INTO phone (type, number, countries_iso_iso2) VALUES ('MOBILE', :number, :iso2)")
        db.execute(phone_query, {"number": data.phone_number, "iso2": data.country_iso})
        phone_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()

        person_phone_query = text("INSERT INTO person_has_phone (person_idperson, phone_idphone) VALUES (:pid, :phid)")
        db.execute(person_phone_query, {"pid": person_id, "phid": phone_id})

        # 4. Crear cuenta con contraseña hasheada
        hashed_pw = hash_password(data.password)
        account_query = text("""
            INSERT INTO accounts (authentication_type_idauthentication_type, email, email_verified, hash_password, is_primary_email) 
            VALUES (1, :email, 0, :hash_pw, 1)
        """)
        db.execute(account_query, {"email": data.email, "hash_pw": hashed_pw})
        account_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()

        # 5. Crear el usuario del sistema
        user_type_id = 1  # 1 = Personal
        user_query = text("""
            INSERT INTO users (idusers, user_type_iduser_type, person_idperson, enabled, verified, preferred_language_code)
            VALUES (:id, :type, :pid, 1, 0, 'en') -- TODO: Obtener idioma del request
        """)
        db.execute(user_query, {"id": person_id, "type": user_type_id, "pid": person_id})

        # 6. Vincular usuario a la cuenta
        user_account_link_query = text("INSERT INTO users_has_accounts (users_idusers, accounts_idaccounts, `default`) VALUES (:uid, :aid, 1)")
        db.execute(user_account_link_query, {"uid": person_id, "aid": account_id})
        
        # Si todo fue bien, confirma todos los cambios en la base de datos
        db.commit()

        # 7. Enviar correo de verificación (después de confirmar la transacción)
        send_verification_email(data.first_name, data.email, person_id)

        # 8. Devolver respuesta de éxito. Esto debe estar DENTRO del try.
        return {"status": "success", "message": "User registered successfully. Please check your email for verification.", "person_id": person_id}

    except HTTPException as http_exc:
        db.rollback() # Revierte los cambios en caso de error de negocio (email duplicado)
        raise http_exc # Vuelve a lanzar la excepción HTTP para que FastAPI la maneje

    except Exception as e:
        # Si ocurre CUALQUIER otro error, revierte todos los cambios en la BD
        db.rollback()
        # Loguea el error para depuración
        print(f"An error occurred: {e}")
        traceback.print_exc()
        # Devuelve un error genérico al cliente
        raise HTTPException(status_code=500, detail={"code": "REG_SERVER_ERROR", "msg": "An unexpected error occurred during registration."})