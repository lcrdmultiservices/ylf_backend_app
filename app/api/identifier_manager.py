from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.database import get_db, get_mongo_db
from app.auth.security import get_current_user
from sqlalchemy import text
from app.utils.mongo_logger import log_error
from app.core import NoTrailingSlashRouter

# Usamos el mismo tipo de router para mantener la consistencia en las URLs
router = NoTrailingSlashRouter(prefix="/identifiers", tags=["Identifier Management"])

# --- Modelos Pydantic para la respuesta ---

# Modelo para un identificador disponible
class AvailableIdentifierOut(BaseModel):
    identifier_id: int
    qr_code: str
    status: str
    identifier_type: str
    product_name: str

# Modelo para un identificador ya asignado a un activo
class AssignedIdentifierOut(BaseModel):
    asset_id: int
    asset_name: str
    asset_description: str | None = None
    qr_code: str
    identifier_type: str
    product_name: str

# Modelo genérico de respuesta que el frontend espera
class IdentifierListResponse(BaseModel):
    items: List[AvailableIdentifierOut] | List[AssignedIdentifierOut]


@router.get("/", response_model=IdentifierListResponse)
async def get_user_identifiers(
    status: str, # El frontend envía 'available' o 'assigned'
    request: Request,
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user),
    mongo_db = Depends(get_mongo_db)
):
    """
    Endpoint unificado para obtener los identificadores de un usuario.
    Filtra por estado para devolver los disponibles o los ya asignados a un activo.
    """
    user_id = int(current_user.get("user_id"))

    if status == 'available':
        # Consulta 1: Identificadores disponibles para el usuario
        query = text("""
            SELECT
                identifier_id,
                qr_code,
                status,
                identifier_type,
                product_name
            FROM
                vw_qr_code_properties
            WHERE
                purchaser_user_id = :user_id
                AND online_delivery = 1
                AND status = 'ASSIGNED_TO_PO'
        """)
        params = {"user_id": user_id}

    elif status == 'assigned':
        # Consulta 2: Activos del usuario con su identificador asignado
        query = text("""
            SELECT
                a.idqr_assets AS asset_id,
                a.asset_name,
                a.asset_description,
                vwp.qr_code,
                vwp.identifier_type,
                vwp.product_name
            FROM
                qr_assets AS a
            JOIN
                vw_qr_code_properties AS vwp ON a.identifier_id = vwp.identifier_id
            WHERE
                a.users_idusers = :user_id
        """)
        params = {"user_id": user_id}
        
    else:
        # Si el parámetro 'status' no es válido, lanzamos un error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid status parameter. Must be 'available' or 'assigned'."
        )

    try:
        results = db.execute(query, params).mappings().all()
        
        # El frontend espera un objeto con una clave "items", así que lo envolvemos
        return {"items": results}

    except Exception as e:
        # Usamos el logger de Mongo en caso de un error de base de datos
        log_error(mongo_db, "/identifiers", "GET", e, user_context={"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error fetching identifiers"
        )