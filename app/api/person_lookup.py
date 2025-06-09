from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy import text

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

@router.post("/lookup-person")
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
        SELECT DISTINCT idperson FROM vw_person_lookup
        WHERE {" OR ".join(conditions)}
        LIMIT 1
    """

    try:
        result = db.execute(text(sql), params).fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if result:
        return {"exists": True, "idperson": result["idperson"]}
    return {"exists": False}