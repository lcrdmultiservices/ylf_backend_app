from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional

# --- CORRECCIÓN 1: Importar la nueva dependencia get_mongo_db ---
from app.db.database import get_db, get_mongo_db
from app.utils.mongo_logger import log_error

router = APIRouter()

class Terms(BaseModel):
    idterms_and_conditions: int
    title: str
    content: str
    version: str

@router.get("/terms/{account_type}/{language_code}", response_model=Optional[Terms])
# --- CORRECCIÓN 2: Inyectar la dependencia de MongoDB ---
# Se añade mongo_db = Depends(get_mongo_db) a la firma de la función.
def get_active_terms(request: Request, account_type: str, language_code: str, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db)):
    """
    Obtiene los términos y condiciones activos para un tipo de cuenta y un idioma.
    """
    document_code_map = {
        "personal": "PATC",
        "business": "BATC",
        "school": "EATC"
    }
    
    search_code = document_code_map.get(account_type)
    
    if not search_code:
        raise HTTPException(status_code=400, detail="Invalid account type")

    query = text("""
        SELECT idterms_and_conditions, title, content, version 
        FROM vw_active_terms_and_conditions
        WHERE language_code = :lang AND doc_type_code = :doc_code
        LIMIT 1
    """)

    try:
        result = db.execute(query, {
            "lang": language_code,
            "doc_code": search_code
        }).fetchone()

        if result:
            return Terms(**result._asdict())

        print(f"WARN: Terms not found for language '{language_code}'. Falling back to 'en'.")
        
        fallback_result = db.execute(query, {
            "lang": "en", 
            "doc_code": search_code
        }).fetchone()
        
        if not fallback_result:
            raise HTTPException(status_code=404, detail=f"Active terms not found for account type '{account_type}' in any language.")
        
        return Terms(**fallback_result._asdict())

    except Exception as e:
        # --- CORRECCIÓN 3: Pasar el objeto mongo_db a log_error ---
        log_error(
            mongo_db=mongo_db,
            endpoint=request.url.path,
            method="GET",
            error=e,
            request_payload={"account_type": account_type, "language_code": language_code},
            user_context={"client_ip": request.client.host if request.client else "N/A"}
        )
        
        raise HTTPException(status_code=500, detail="error_fetching_terms")