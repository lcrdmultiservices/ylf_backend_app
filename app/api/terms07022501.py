from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional

# Importa la función get_db desde tu archivo de base de datos
from app.db.database import get_db

router = APIRouter()

# --- Modelo Pydantic para la respuesta ---
class Terms(BaseModel):
    title: str
    content: str
    version: str

# --- Endpoint para obtener los términos y condiciones ---
@router.get("/terms/{account_type}/{language_code}", response_model=Optional[Terms])
def get_active_terms(account_type: str, language_code: str, db: Session = Depends(get_db)):
    """
    Obtiene los términos y condiciones activos para un tipo de cuenta y un idioma.
    - account_type: 'personal', 'business', 'school'
    - language_code: 'en', 'es', 'pt'
    """
    # Mapeo simple del tipo de cuenta a lo que podría estar en la BD
    # Esto se puede hacer más robusto en el futuro
    document_type_map = {
        "personal": "Personal",
        "business": "Business",
        "school": "Educational"
    }
    
    search_term = document_type_map.get(account_type)
    
    if not search_term:
        raise HTTPException(status_code=400, detail="Invalid account type")

    query = text("""
        SELECT title, content, version 
        FROM vw_active_terms_and_conditions
        WHERE language_code = :lang AND document_type_name LIKE :doc_type
        LIMIT 1
    """)

    try:
        result = db.execute(query, {
            "lang": language_code,
            "doc_type": f"%{search_term}%"
        }).fetchone()

        if not result:
            # Si no se encuentran términos para el idioma específico, intenta con inglés como fallback
            fallback_result = db.execute(query, {
                "lang": "en",
                "doc_type": f"%{search_term}%"
            }).fetchone()
            
            if not fallback_result:
                return None # Devuelve null si no se encuentra nada
            
            return Terms(**fallback_result._asdict())

        return Terms(**result._asdict())

    except Exception as e:
        print(f"Database error fetching terms: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch terms and conditions.")
