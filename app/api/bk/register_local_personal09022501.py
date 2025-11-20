from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text
import bcrypt
from typing import Optional
# --- CORRECCIÓN: Se añade la importación que faltaba ---
from datetime import datetime, timezone

# Importaciones de nuestro proyecto
from app.db.database import get_db, get_mongo_db 
from app.utils.mongo_logger import log_error
from app.utils.mailgun_client import send_verification_email
# MODIFICADO: Ahora importamos desde el nuevo manejador de OTP
from app.utils.otp_handler import generate_and_store_otp

router = APIRouter()

# Se mantiene el modelo Pydantic completo del usuario
class RegisterLocalUser(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    birth_date: str
    phone_number: str
    country_iso: str
    password: str
    terms_id: int
    marketing_accepted: bool
    anonymous_consent_id: Optional[str] = None
    language: str = 'en'

# --- Las funciones de ayuda para el consentimiento y hash se mantienen ---
def log_consent_to_mongo(mongo_db, user_id: int, process_key: str, option_key: str, status: str, version_id: Optional[int], request: Request):
    if mongo_db is None: return
    try:
        consent_log_collection = mongo_db.consent_logs
        consent_document = { "user_id": user_id, "anonymous_id": None, "process_key": process_key, "option_key": option_key, "status": status, "version_id": version_id, "ip_address": request.client.host if request.client else "N/A", "user_agent": request.headers.get('user-agent', 'Unknown'), "timestamp": datetime.now(timezone.utc) }
        consent_log_collection.insert_one(consent_document)
    except Exception as e:
        log_error(mongo_db=mongo_db, endpoint="/register/local/personal", method="POST-MONGO-CONSENT", error=e, request_payload={"user_id": user_id, "process_key": process_key})

def associate_anonymous_consent(mongo_db, user_id: int, anonymous_id: str):
    if mongo_db is None or anonymous_id is None: return
    try:
        consent_log_collection = mongo_db.consent_logs
        consent_log_collection.update_many( {"anonymous_id": anonymous_id}, {"$set": {"user_id": user_id}} )
    except Exception as e:
        log_error(mongo_db=mongo_db, endpoint="/register/local/personal", method="POST-MONGO-ASSOCIATE", error=e, request_payload={"user_id": user_id, "anonymous_id": anonymous_id})

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')


@router.post("/register/local/personal", status_code=201)
def register_local_user(data: RegisterLocalUser, request: Request, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db)):
    
    person_id = None
    try:
        # Se mantiene toda la lógica de creación de usuario en MySQL
        existing_account = db.execute(text("SELECT idaccounts FROM accounts WHERE email = :email"), {"email": data.email}).fetchone()
        if existing_account:
            raise HTTPException(status_code=409, detail="error_email_exists")
        
        person_query = text("INSERT INTO person (first_name, last_name, email, dob, status) VALUES (:fn, :ln, :email, :dob, 'pending')")
        db.execute(person_query, {"fn": data.first_name, "ln": data.last_name, "email": data.email, "dob": data.birth_date})
        person_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        
        phone_query = text("INSERT INTO phone (type, number, countries_iso_iso2) VALUES ('MOBILE', :num, :iso)")
        db.execute(phone_query, {"num": data.phone_number, "iso": data.country_iso})
        phone_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        
        person_phone_query = text("INSERT INTO person_has_phone (person_idperson, phone_idphone) VALUES (:pid, :phid)")
        db.execute(person_phone_query, {"pid": person_id, "phid": phone_id})
        
        hashed_pw = hash_password(data.password)
        account_query = text("INSERT INTO accounts (authentication_type_idauthentication_type, email, email_verified, hash_password, is_primary_email) VALUES (1, :email, 0, :hash_pw, 1)")
        db.execute(account_query, {"email": data.email, "hash_pw": hashed_pw})
        account_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        
        user_query = text("INSERT INTO users (idusers, user_type_iduser_type, person_idperson, enabled, verified) VALUES (:id, 1, :pid, 1, 0)")
        db.execute(user_query, {"id": person_id, "pid": person_id})
        
        user_account_link_query = text("INSERT INTO users_has_accounts (users_idusers, accounts_idaccounts, `default`) VALUES (:uid, :aid, 1)")
        db.execute(user_account_link_query, {"uid": person_id, "aid": account_id})
        db.commit()
    except Exception as e:
        db.rollback()
        log_error(mongo_db=mongo_db, endpoint="/register/local/personal", method="POST-MYSQL", error=e, request_payload=data.dict())
        raise HTTPException(status_code=500, detail="error_registration_failed")

    # Se mantiene la lógica de consentimientos
    if data.anonymous_consent_id:
        associate_anonymous_consent(mongo_db, user_id=person_id, anonymous_id=data.anonymous_consent_id)
    log_consent_to_mongo(mongo_db, user_id=person_id, process_key='terms_acceptance_personal', option_key='accept_terms_personal', status='granted', version_id=data.terms_id, request=request)
    if data.marketing_accepted:
        log_consent_to_mongo(mongo_db, user_id=person_id, process_key='marketing_emails_opt_in', option_key='allow_marketing_emails', status='granted', version_id=None, request=request)
    else:
        log_consent_to_mongo(mongo_db, user_id=person_id, process_key='marketing_emails_opt_in', option_key='allow_marketing_emails', status='denied', version_id=None, request=request)

    # La llamada a generate_and_store_otp ahora usa la función importada
    otp_code = generate_and_store_otp(mongo_db, user_id=person_id, email=data.email, otp_context="ACCOUNT_REGISTRATION")
    
    if otp_code:
        send_verification_email(email_to=data.email, otp_code=otp_code, first_name=data.first_name, language=data.language)
    else:
        raise HTTPException(status_code=500, detail="error_otp_generation_failed")

    return {"status": "success_pending_verification", "message": "User registered. Please check your email for verification code.", "userId": person_id}

# Las funciones generate_and_store_otp y verify_otp han sido eliminadas de este archivo
# y ahora se importan desde app/utils/otp_handler.py
