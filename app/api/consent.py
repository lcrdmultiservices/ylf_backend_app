from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text

# Importar las dependencias de las bases de datos y el logger
from app.db.database import get_db, get_mongo_db 
from app.utils.mongo_logger import log_error

router = APIRouter()

class AnonymousConsentRequest(BaseModel):
    choices: Dict[str, bool]

@router.get("/consents/options/{language_code}")
# Se añade la dependencia de mongo_db para poder registrar errores
def get_consent_options(language_code: str, request: Request, db: Session = Depends(get_db), mongo_db = Depends(get_mongo_db)):
    """
    Obtiene todos los procesos de consentimiento activos y no obligatorios
    desde la vista vw_active_consent_requirements.
    """
    # --- CORRECCIÓN: Se usan los nombres de columna correctos de la vista y se elimina el filtro de idioma ---
    # La vista tiene 'process_name' y 'process_description'. Los renombramos con 'AS' para que coincidan con la expectativa original.
    # El filtro por 'language_code' se eliminó porque la vista no contiene esa información.
    query = text("""
        SELECT 
            process_key, 
            process_name AS name, 
            provider, 
            process_description AS description, 
            policy_url, 
            available_options_json
        FROM vw_active_consent_requirements
        WHERE is_mandatory = 0
    """)
    
    try:
        # La consulta ya no necesita parámetros de idioma
        results = db.execute(query).fetchall()

        if not results:
            return []

        return [dict(row._mapping) for row in results]
    except Exception as e:
        # Se añade el logging de errores a este endpoint para mayor robustez
        log_error(
            mongo_db=mongo_db,
            endpoint=request.url.path,
            method="GET",
            error=e,
            request_payload={"language_code": language_code},
            user_context={"client_ip": request.client.host if request.client else "N/A"}
        )
        raise HTTPException(status_code=500, detail="Could not fetch consent options.")


@router.post("/consents/anonymous", status_code=201)
def log_anonymous_consent(data: AnonymousConsentRequest, request: Request, mongo_db = Depends(get_mongo_db)):
    """
    Registra las decisiones de consentimiento de un usuario anónimo en MongoDB.
    """
    anonymous_id = str(uuid.uuid4())
    
    if mongo_db is None:
        raise HTTPException(status_code=500, detail="Logging service is not available.")

    try:
        consent_log_collection = mongo_db.consent_logs
        logs_to_insert = []
        
        timestamp = datetime.now(timezone.utc)
        ip_address = request.client.host if request.client else "N/A"
        user_agent = request.headers.get('user-agent', 'Unknown')

        for option_key, granted in data.choices.items():
            log_entry = {
                "anonymous_id": anonymous_id,
                "user_id": None,
                "option_key": option_key,
                "status": "granted" if granted else "denied",
                "version_id": None,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "timestamp": timestamp
            }
            logs_to_insert.append(log_entry)

        if logs_to_insert:
            consent_log_collection.insert_many(logs_to_insert)
        
        return {"status": "success", "anonymous_id": anonymous_id}

    except Exception as e:
        log_error(
            mongo_db=mongo_db,
            endpoint="/consents/anonymous",
            method="POST",
            error=e,
            request_payload=data.dict(),
            user_context={"client_ip": ip_address}
        )
        raise HTTPException(status_code=500, detail="Could not save consent preferences.")
