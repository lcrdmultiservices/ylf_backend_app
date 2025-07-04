from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from datetime import datetime
from sqlalchemy.orm import Session
import pymysql
import traceback

router = APIRouter()

class RegisterLocalUser(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    birth_date: str  # ISO string
    phone_number: str
    country_code: str
    password: str

@router.post("/register/local/personal")
async def register_local_user(data: RegisterLocalUser, request: Request):
    try:
        conn = pymysql.connect(...)  # define your DB connection
        cursor = conn.cursor()
        conn.begin()

        # 1. Insert person
        cursor.execute("""
            INSERT INTO person (first_name, last_name, email, dob, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (data.first_name, data.last_name, data.email, data.birth_date, 'pending'))
        person_id = cursor.lastrowid

        # 2. Insert phone and person_has_phone
        cursor.execute("""
            INSERT INTO phone (type, number, countries_iso_iso2)
            VALUES ('MOBILE', %s, %s)
        """, (data.phone_number, data.country_code))
        phone_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO person_has_phone (person_idperson, phone_idphone)
            VALUES (%s, %s)
        """, (person_id, phone_id))

        # 3. Insert into person_identifiers
        cursor.execute("""
            INSERT INTO person_identifiers (
                idperson_identifiers, person_idperson, identifier_type,
                identifier_value, is_primary, is_verified, origin_type
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            person_id, person_id, 'email', data.email,
            1, 0, 'manual'
        ))

        # 4. Create account
        # Simula hashing (usa bcrypt/scrypt real en producción)
        hash_pw = f"hash({data.password})"
        cursor.execute("""
            INSERT INTO accounts (
                authentication_type_idauthentication_type, email, email_verified,
                hash_password, is_primary_email
            ) VALUES (%s, %s, %s, %s, %s)
        """, (1, data.email, 0, hash_pw, 1))
        account_id = cursor.lastrowid

        # 5. Create user
        user_type_id = 1  # Asumimos 1 = personal
        cursor.execute("""
            INSERT INTO users (idusers, user_type_iduser_type, person_idperson, enabled, verified)
            VALUES (%s, %s, %s, %s, %s)
        """, (person_id, user_type_id, person_id, 1, 0))

        # 6. Link user to account
        cursor.execute("""
            INSERT INTO users_has_accounts (users_idusers, accounts_idaccounts, `default`)
            VALUES (%s, %s, %s)
        """, (person_id, account_id, 1))

        conn.commit()

        # TODO: Send verification email using Mailgun

        return {"status": "success", "message": "registered", "person_id": person_id}

    except Exception as e:
        conn.rollback()
        with open("insert_error_log.txt", "a") as log:
            log.write(f"[{datetime.now()}] {str(e)}\n{traceback.format_exc()}\n\n")
        raise HTTPException(status_code=500, detail={"code": "REG_ERR", "msg": "Registration failed"})

    finally:
        cursor.close()
        conn.close()
