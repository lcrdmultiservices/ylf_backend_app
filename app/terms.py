# Se añade 'Request' a las importaciones
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
# Se importa la función de logging
from app.utils.mongo_logger import log_error

router = APIRouter()

class Terms(BaseModel):
    idterms_and_conditions: int
    title: str
    content: str
    version: str

@router.get("/terms/{account_type}/{language_code}", response_model=Optional[Terms])
# Se añade 'request: Request' a la función
def get_active_terms(request: Request, account_type: str, language_code: str, db: Session = Depends(get_db)):
    """
    Obtiene los términos y condiciones activos para un tipo de cuenta y un idioma.
    """
    # --- CORRECCIÓN 1: Mapear al código del documento (ej. 'PATC') en lugar del nombre. ---
    # Esto hace la búsqueda exacta y más confiable.
    document_code_map = {
        "personal": "PATC",
        "business": "BATC",
        "school": "EATC"
    }
    
    search_code = document_code_map.get(account_type)
    
    if not search_code:
        raise HTTPException(status_code=400, detail="Invalid account type")

    # --- CORRECCIÓN 2: La consulta ahora filtra por `doc_type_code` con una coincidencia exacta. ---
    # Se eliminó el `LIKE` y se usa `=` para mayor precisión y rendimiento.
    query = text("""
        SELECT idterms_and_conditions, title, content, version 
        FROM vw_active_terms_and_conditions
        WHERE language_code = :lang AND doc_type_code = :doc_code
        LIMIT 1
    """)

    try:
        # --- CORRECCIÓN 3: Se pasa `doc_code` en lugar de `doc_type` a los parámetros. ---
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
        # Se implementa el registro de errores en MongoDB
        log_error(
            endpoint=request.url.path,
            method="GET",
            error=e,
            # Para peticiones GET, el "payload" son los parámetros de la ruta.
            request_payload={"account_type": account_type, "language_code": language_code},
            user_context={"client_ip": request.client.host if request.client else "N/A"}
        )
        
        # Se devuelve un error genérico al usuario.
        raise HTTPException(status_code=500, detail="error_fetching_terms")
