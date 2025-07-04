from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text
import traceback
import requests
import os
import bcrypt

# Importamos la dependencia get_db
from app.db.database import get_db

router = APIRouter()

# --- Modelo Pydantic Actualizado ---
# Ahora coincide exactamente con lo que envía el frontend
class RegisterLocalUser(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    birth_date: str
    phone_number: str
    country_iso: str # <-- CORREGIDO: Acepta 'country_iso'
    password: str
    terms_id: int    # <-- CORREGIDO: Acepta 'terms_id'

# --- Lógica de Hashing (sin cambios) ---
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

# --- Lógica de Envío de Correo (sin cambios) ---
def send_verification_email(first_name: str, email: str, person_id: int):
    # (Tu código de Mailgun se mantiene aquí sin cambios)
    pass # Placeholder para brevedad

@router.post("/register/local/personal", status_code=201)
def register_local_user(data: RegisterLocalUser, request: Request, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario personal, manejando todas las inserciones
    en una única transacción de base de datos.
    """
    # 1. Verificar si el email ya existe
    existing_account = db.execute(text("SELECT idaccounts FROM accounts WHERE email = :email"), {"email": data.email}).fetchone()
    if existing_account:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    try:
        # --- Inicia la transacción ---
        db.begin()

        # 2. Insertar en `person`
        person_query = text("INSERT INTO person (first_name, last_name, email, dob, status) VALUES (:fn, :ln, :email, :dob, 'pending')")
        db.execute(person_query, {"fn": data.first_name, "ln": data.last_name, "email": data.email, "dob": data.birth_date})
        person_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()

        # 3. Insertar en `phone` y `person_has_phone`
        phone_query = text("INSERT INTO phone (type, number, countries_iso_iso2) VALUES ('MOBILE', :num, :iso)")
        db.execute(phone_query, {"num": data.phone_number, "iso": data.country_iso})
        phone_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        person_phone_query = text("INSERT INTO person_has_phone (person_idperson, phone_idphone) VALUES (:pid, :phid)")
        db.execute(person_phone_query, {"pid": person_id, "phid": phone_id})

        # 4. Crear la cuenta en `accounts`
        hashed_pw = hash_password(data.password)
        account_query = text("INSERT INTO accounts (authentication_type_idauthentication_type, email, email_verified, hash_password, is_primary_email) VALUES (1, :email, 0, :hash_pw, 1)")
        db.execute(account_query, {"email": data.email, "hash_pw": hashed_pw})
        account_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()

        # 5. Crear el registro en `users`
        user_query = text("INSERT INTO users (idusers, user_type_iduser_type, person_idperson, enabled, verified) VALUES (:id, 1, :pid, 1, 0)")
        db.execute(user_query, {"id": person_id, "pid": person_id})

        # 6. Vincular en `users_has_accounts`
        user_account_link_query = text("INSERT INTO users_has_accounts (users_idusers, accounts_idaccounts, `default`) VALUES (:uid, :aid, 1)")
        db.execute(user_account_link_query, {"uid": person_id, "aid": account_id})

        # 7. Registrar la aceptación de los términos
        ip_address = request.client.host
        user_agent = request.headers.get('user-agent', 'Unknown')
        terms_query = text("INSERT INTO users_terms_acceptance (users_idusers, terms_and_conditions_idterms_and_conditions, ip_address, user_Agent) VALUES (:uid, :tid, :ip, :ua)")
        db.execute(terms_query, {"uid": person_id, "tid": data.terms_id, "ip": ip_address, "ua": user_agent})
        
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"Error en el registro: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="An internal error occurred during registration.")

    send_verification_email(data.first_name, data.email, person_id)

    return {"status": "success", "message": "User registered successfully. Please check your email for verification.", "userId": person_id}
