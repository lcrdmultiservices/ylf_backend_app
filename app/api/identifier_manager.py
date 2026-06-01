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

class ActivateRequest(BaseModel):
    qr_code: str
    asset_id: int | None = None

class StatusUpdate(BaseModel):
    status: str

class IdentifierOut(BaseModel):
    identifier_id: int
    qr_code: str
    status: str
    identifier_type: str
    owner_user_id: int | None = None
    asset_id: int | None = None

ALLOWED_TRANSITIONS = {
    'ACTIVATED': {'LOST', 'DONATED', 'DECOMMISSIONED'}
}


@router.get("/", response_model=IdentifierListResponse)
async def get_user_identifiers(
    filter_status: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    mongo_db = Depends(get_mongo_db)
):
    user_id = int(current_user.get("user_id"))

    if filter_status == 'available':
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

    elif filter_status == 'assigned':
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
        raise HTTPException(
            status_code=400,
            detail="Invalid filter_status parameter. Must be 'available' or 'assigned'."
        )

    try:
        results = db.execute(query, params).mappings().all()
        return {"items": results}

    except Exception as e:
        log_error(mongo_db, "/identifiers", "GET", e, user_context={"user_id": user_id})
        raise HTTPException(status_code=500, detail="Error fetching identifiers")


@router.post("/activate", response_model=IdentifierOut)
async def activate_identifier(
    payload: ActivateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    mongo_db = Depends(get_mongo_db)
):
    user_id = int(current_user.get("user_id"))

    # 1. Buscar QR por código y verificar que pertenece al usuario
    qr_row = db.execute(
        text("""
            SELECT idqr_codes, status, purchaser_user_id, identifier_type
            FROM identifiers
            WHERE code = :qr_code
        """),
        {"qr_code": payload.qr_code}
    ).first()

    if not qr_row:
        raise HTTPException(status_code=404, detail="QR code not found")
    if qr_row.purchaser_user_id != user_id:
        raise HTTPException(status_code=403, detail="QR code does not belong to this user")
    if qr_row.status != 'ASSIGNED_TO_PO':
        raise HTTPException(status_code=409, detail=f"QR is not activatable. Current status: {qr_row.status}")

    qr_id = qr_row.idqr_codes

    # 2. Si viene asset_id, verificar que el item pertenece al usuario
    if payload.asset_id is not None:
        asset = db.execute(
            text("SELECT idqr_assets FROM qr_assets WHERE idqr_assets = :asset_id AND users_idusers = :user_id"),
            {"asset_id": payload.asset_id, "user_id": user_id}
        ).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found or does not belong to this user")

    try:
        db.execute(
            text("UPDATE identifiers SET status = 'ACTIVATED', owner_user_id = :user_id WHERE idqr_codes = :qr_id"),
            {"user_id": user_id, "qr_id": qr_id}
        )
        if payload.asset_id is not None:
            db.execute(
                text("UPDATE qr_assets SET qr_code_id = :qr_id WHERE idqr_assets = :asset_id AND users_idusers = :user_id"),
                {"qr_id": qr_id, "asset_id": payload.asset_id, "user_id": user_id}
            )
        db.commit()
    except Exception as e:
        db.rollback()
        log_error(mongo_db, "/identifiers/activate", "POST", e,
                  request_payload=payload.dict(), user_context={"user_id": user_id})
        raise HTTPException(status_code=500, detail="Failed to activate identifier")

    updated = db.execute(
        text("""
            SELECT idqr_codes AS identifier_id, code AS qr_code, status,
                   identifier_type, owner_user_id
            FROM identifiers WHERE idqr_codes = :qr_id
        """),
        {"qr_id": qr_id}
    ).mappings().first()

    return {**dict(updated), "asset_id": payload.asset_id}


@router.put("/{identifier_id}/status", response_model=IdentifierOut)
async def update_identifier_status(
    identifier_id: int,
    payload: StatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    mongo_db = Depends(get_mongo_db)
):
    user_id = int(current_user.get("user_id"))

    # 1. Verificar que el QR existe y pertenece al usuario como owner
    qr_row = db.execute(
        text("""
            SELECT idqr_codes, status, identifier_type
            FROM identifiers
            WHERE idqr_codes = :identifier_id AND owner_user_id = :user_id
        """),
        {"identifier_id": identifier_id, "user_id": user_id}
    ).first()

    if not qr_row:
        raise HTTPException(status_code=404, detail="Identifier not found")

    # 2. Verificar que la transición está permitida
    allowed = ALLOWED_TRANSITIONS.get(qr_row.status, set())
    if payload.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot transition from '{qr_row.status}' to '{payload.status}'. Allowed: {sorted(allowed)}"
        )

    try:
        db.execute(
            text("UPDATE identifiers SET status = :new_status WHERE idqr_codes = :identifier_id AND owner_user_id = :user_id"),
            {"new_status": payload.status, "identifier_id": identifier_id, "user_id": user_id}
        )
        db.commit()
    except Exception as e:
        db.rollback()
        log_error(mongo_db, f"/identifiers/{identifier_id}/status", "PUT", e,
                  request_payload=payload.dict(), user_context={"user_id": user_id})
        raise HTTPException(status_code=500, detail="Failed to update identifier status")

    # 3. Retornar el QR actualizado con su asset vinculado si existe
    updated = db.execute(
        text("""
            SELECT i.idqr_codes AS identifier_id, i.code AS qr_code, i.status,
                   i.identifier_type, i.owner_user_id,
                   a.idqr_assets AS asset_id
            FROM identifiers i
            LEFT JOIN qr_assets a ON a.qr_code_id = i.idqr_codes AND a.users_idusers = :user_id
            WHERE i.idqr_codes = :identifier_id
        """),
        {"identifier_id": identifier_id, "user_id": user_id}
    ).mappings().first()

    return dict(updated)