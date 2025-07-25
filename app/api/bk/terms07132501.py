from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db

router = APIRouter()

class Terms(BaseModel):
    idterms_and_conditions: int
    title: str
    content: str
    version: str

# --- CORRECCIÓN 1: Se restaura la ruta original ---
# Volvemos a incluir {language_code} como parte de la ruta.
@router.get("/terms/{account_type}/{language_code}", response_model=Optional[Terms])
def get_active_terms(account_type: str, language_code: str, db: Session = Depends(get_db)):
    """
    Obtiene los términos y condiciones activos para un tipo de cuenta y un idioma.
    """
    document_type_map = {
        "personal": "Personal",
        "business": "Business",
        "school": "Educational"
    }
    
    search_term = document_type_map.get(account_type)
    
    if not search_term:
        raise HTTPException(status_code=400, detail="Invalid account type")

    query = text("""
        SELECT idterms_and_conditions, title, content, version 
        FROM vw_active_terms_and_conditions
        WHERE language_code = :lang AND document_type_name LIKE :doc_type
        LIMIT 1
    """)

    try:
        # Intenta obtener los términos en el idioma solicitado
        result = db.execute(query, {
            "lang": language_code,
            "doc_type": f"%{search_term}%"
        }).fetchone()

        if result:
            # Si se encuentra, lo devuelve
            return Terms(**result._asdict())

        # --- CORRECIÓN 2: Lógica de Fallback mejorada ---
        # Si no se encontró, se imprime un aviso en la consola del servidor
        # y se intenta con el idioma de respaldo (inglés).
        print(f"WARN: Terms not found for language '{language_code}'. Falling back to 'en'.")
        
        fallback_result = db.execute(query, {
            "lang": "en", 
            "doc_type": f"%{search_term}%"
        }).fetchone()
        
        if not fallback_result:
            # Si tampoco hay en inglés, ahora sí se lanza un error.
            raise HTTPException(status_code=404, detail=f"Active terms not found for account type '{account_type}' in any language.")
        
        return Terms(**fallback_result._asdict())

    except Exception as e:
        print(f"Database error fetching terms: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch terms and conditions.")