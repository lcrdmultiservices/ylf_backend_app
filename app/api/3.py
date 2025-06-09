from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from pydantic import BaseModel, EmailStr
from typing import Optional
import traceback

from app.db.database import SessionLocal

router = APIRouter()

# Modelo de solicitud
class PersonLookupRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    birth_date: Optional[str] = None  # formato YYYY-MM-DD

# Dependencia para obtener sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/lookup-person/")
def lookup_person(data: PersonLookupRequest, db: Session = Depends(get_db)):
    if not (data.email or data.phone_number or data.birth_date):
        raise HTTPException(status_code=400, detail="At least one field must be provided.")

    conditions = []
    params = {}

    if data.email:
        conditions.append("""
            (person_email = :email OR identifier_email = :email OR account_email = :email)
        """)
        params["email"] = data.email

    if data.phone_number:
        conditions.append("phone_number = :phone_number")
        params["phone_number"] = data.phone_number

    if data.birth_date:
        conditions.append("birth_date = :birth_date")
        params["birth_date"] = data.birth_date

    sql = f"""
        SELECT idperson FROM vw_person_lookup LIMIT 1
    """

   try:
        print("Ejecutando SQL:", sql)
        print("Parámetros:", params)
        result = db.execute(text(sql), params).fetchone()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

