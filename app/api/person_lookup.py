from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy import text

# --- CORRECCIÓN 1: Importar la nueva dependencia get_mongo_db ---
from app.db.database import get_db, get_mongo_db
from app.utils.mongo_logger import log_error

router = APIRouter()

class PersonLookupRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    birth_date: Optional[str] = None

@router.post("/lookup-person")
# --- CORRECCIÓN 2: Inyectar la dependencia de MongoDB ---
# Se añade mongo_db = Depends(get_mongo_db) a la firma de la función.
def lookup_person(data: PersonLookupRequest, request: Request, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db)):
    if not (data.email or data.phone_number or data.birth_date or (data.first_name and data.last_name)):
        raise HTTPException(status_code=400, detail="At least one field or first/last name pair must be provided.")

    conditions = []
    params = {}

    if data.first_name and data.last_name:
        conditions.append("(first_name = :first_name AND last_name = :last_name)")
        params["first_name"] = data.first_name
        params["last_name"] = data.last_name

    if data.email:
        conditions.append("(person_primary_email = :email OR account_email = :email)")
        params["email"] = data.email

    if data.phone_number:
        conditions.append("phone_number = :phone_number")
        params["phone_number"] = data.phone_number

    if data.birth_date:
        conditions.append("dob = :birth_date")
        params["birth_date"] = data.birth_date

    sql = f"""
        SELECT DISTINCT idperson FROM vw_person_lookup
        WHERE {" OR ".join(conditions)}
        LIMIT 1
    """

    try:
        result = db.execute(text(sql), params).fetchone()

        if result:
            return {"exists": True, "idperson": result.idperson}
        
        return {"exists": False}

    except Exception as e:
        # --- CORRECCIÓN 3: Pasar el objeto mongo_db a log_error ---
        # Ahora la función de logging recibe la conexión a la base de datos.
        log_error(
            mongo_db=mongo_db,
            endpoint="/lookup-person",
            method="POST",
            error=e,
            request_payload=data.dict(),
            user_context={"client_ip": request.client.host if request.client else "N/A"}
        )
        raise HTTPException(
            status_code=500,
            detail="error_lookup_failed"
        )
