import os
import uuid
import magic
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from typing import List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.auth.security import get_current_user
from sqlalchemy import text
from app.utils.mongo_logger import log_error
from app.db.database import get_mongo_db
from app.core import limiter, NoTrailingSlashRouter


router = NoTrailingSlashRouter(prefix="/assets", tags=["Asset Management"])

# --- Modelos Pydantic para la creación de activos ---
class AssetCreate(BaseModel):
    asset_name: str
    asset_description: str | None = None
    asset_color: str | None = None
    asset_serial: str | None = None
    group_id: int | None = None
    parent_asset_id: int | None = None
    item_type_id: int # El id del tipo de la tabla asset_types

class AssetDetailOut(BaseModel):
    idqr_assets: int
    asset_name: str
    asset_color: str | None = None
    asset_serial: str | None = None
    asset_description: str | None = None
    group_id: int | None = None
    parent_asset_id: int | None = None
    iditem_types: int
    status: str
    image_url: str | None = None
    receipt_url: str | None = None

class AssetUpdate(BaseModel):
    asset_name: str
    asset_description: str | None = None
    asset_color: str | None = None
    asset_serial: str | None = None
    group_id: int | None = None
    parent_asset_id: int | None = None
    iditem_types: int
    

# --- Constantes de Configuración de Archivos ---
MEDIA_ROOT = "media" # Asegúrate que esta carpeta exista en la raíz de tu proyecto
os.makedirs(MEDIA_ROOT, exist_ok=True)


@router.post("/", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_asset(request: Request, asset_data: AssetCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user), mongo_db = Depends(get_mongo_db)):
    user_id = int(current_user.get("user_id"))
    
    if not asset_data.asset_name.strip() or not asset_data.item_type_id:
       raise HTTPException(status_code=422, detail="Asset name and type are required")
    
    
    query = text("""
    INSERT INTO qr_assets (users_idusers, asset_name, asset_description, asset_color, asset_serial, group_id, parent_asset_id, iditem_types, status, activation_date)
    VALUES (:user_id, :asset_name, :desc, :color, :serial, :group_id, :parent_id, :type_id, 'ACTIVE', NOW())
""")
    
    try:
        result = db.execute(query, {
            "user_id": user_id,
            "asset_name": asset_data.asset_name,
            "desc": asset_data.asset_description,
            "color": asset_data.asset_color,
            "serial": asset_data.asset_serial,
            "group_id": asset_data.group_id,
            "parent_id": asset_data.parent_asset_id,
            "type_id": asset_data.item_type_id,
            
        })
        db.commit()
        new_asset_id = result.lastrowid
        
        # Devolvemos el ID del activo recién creado para que el frontend pueda subir adjuntos
        return {"idqr_assets": new_asset_id}
        
    except Exception as e:
        db.rollback()
        # Aquí podrías usar tu logger de Mongo
        log_error(mongo_db, "/assets", "POST", e, request_payload=asset_data.dict(), user_context={"user_id": user_id})
        raise HTTPException(status_code=500, detail="Failed to create asset")


@router.post("/{asset_id}/attachments", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def upload_asset_attachment(
    request: Request,
    asset_id: int, 
    use: str,
    file: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user),
    mongo_db = Depends(get_mongo_db)
):
    user_id = int(current_user.get("user_id"))
    
    # 1. Verificar que el asset pertenece al usuario (sin cambios)
    asset_check_query = text("SELECT idqr_assets FROM qr_assets WHERE idqr_assets = :asset_id AND users_idusers = :user_id")
    if not db.execute(asset_check_query, {"asset_id": asset_id, "user_id": user_id}).first():
        raise HTTPException(status_code=404, detail="Asset not found or permission denied")
    
    # 2. Leer contenido y validar (sin cambios)
    file_content = await file.read()
    await file.seek(0)
    
    detected_mime_type = magic.from_buffer(file_content, mime=True)
    allowed_mime_types = ['image/jpeg', 'image/png', 'application/pdf']
    
    if detected_mime_type not in allowed_mime_types:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {detected_mime_type}")

    # 3. Guardar el archivo en el servidor (con corrección)
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(MEDIA_ROOT, unique_filename)
    
    with open(file_path, "wb") as buffer:
        # ✅ CAMBIO 1: Escribimos el contenido que ya habíamos leído, en lugar de leerlo de nuevo.
        buffer.write(file_content)

    # 4. Guardar la referencia en la base de datos (con correcciones)
    file_url = f"/{MEDIA_ROOT}/{unique_filename}"
    
    attachment_query = text("""
        INSERT INTO asset_attachments (asset_id, attachment_type, file_url, mime_type, original_filename, file_size_bytes)
        VALUES (:asset_id, :type, :url, :mime, :orig_name, :size)
    """)
    
    try:
        db.execute(attachment_query, {
            "asset_id": asset_id,
            "type": use,  # ✅ CAMBIO 2: El parámetro ahora es 'type', coincidiendo con el :type del query.
            "url": file_url,
            "mime": file.content_type,
            "orig_name": file.filename,
            "size": len(file_content) # ✅ CAMBIO 3: Usamos el tamaño real del contenido leído.
        })
        db.commit()
    except Exception as e:
        db.rollback()
        os.remove(file_path) # Si falla la BD, borramos el archivo subido
        log_error(mongo_db, f"/assets/{asset_id}/attachments", "POST", e, user_context={"user_id": user_id})
        raise HTTPException(status_code=500, detail="Failed to save attachment metadata")

    return {"filename": unique_filename, "file_url": file_url}
    
class ContainerOut(BaseModel):
    idqr_assets: int
    asset_name: str
    parent_asset_id: int | None

@router.get("/containers", response_model=List[ContainerOut])
async def get_user_containers(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Obtiene todos los assets del usuario cuyo TIPO está marcado como 'contenedor',
    y asegura que solo se listen los del usuario actual.
    """
    user_id = int(current_user.get("user_id"))
    
    # --- INICIO DE LA CONSULTA CORREGIDA ---
    # Esta consulta une los activos con sus tipos y filtra por el usuario
    # y por la bandera 'can_be_container'.
    query = text("""
        SELECT
            a.idqr_assets,
            a.asset_name,
            a.parent_asset_id
        FROM
            qr_assets AS a
        JOIN
            asset_types AS t ON a.iditem_types = t.type_id
        WHERE
            a.users_idusers = :user_id 
            AND t.can_be_container = 1
    """)
    # --- FIN DE LA CONSULTA CORREGIDA ---
    
    try:
        results = db.execute(query, {"user_id": user_id}).fetchall()

        # El mapeo explícito que ya teníamos sigue siendo correcto y necesario
        container_list = [ContainerOut(
            idqr_assets=row.idqr_assets,
            asset_name=row.asset_name,
            parent_asset_id=row.parent_asset_id
        ) for row in results]
        
        return container_list

    except Exception as e:
        # Aquí podrías usar tu mongo_logger
        raise HTTPException(status_code=500, detail="Error fetching containers")
        
# --- Modelos Pydantic para la respuesta del listado ---

class AssetOut(BaseModel):
    id: int
    asset_name: str
    color: str | None = None
    item_type_name: str
    group_name: str | None = None
    has_qr_code: bool
    is_container: bool
    contained_items_count: int
    image_url: str | None = None

    class Config:
        orm_mode = True

class PaginationOut(BaseModel):
    current_page: int
    has_more_pages: bool
    total_items: int

class AssetListResponse(BaseModel):
    items: List[AssetOut]
    pagination: PaginationOut


# --- Endpoint para el listado paginado de activos ---

@router.get("/", response_model=AssetListResponse)
async def get_all_assets(
    page: int = 1, 
    limit: int = 10, 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    user_id = int(current_user.get("user_id"))
    
    # 1. Calcular el offset para la paginación
    offset = (page - 1) * limit

    # 2. Obtener el número total de ítems para el usuario (para la paginación)
    total_items_query = text("SELECT COUNT(*) FROM qr_assets WHERE users_idusers = :user_id AND status != 'DELETED'")
    total_items = db.execute(total_items_query, {"user_id": user_id}).scalar_one()

    # 3. Consulta principal para obtener los datos de los ítems de forma paginada
    #    Esta consulta es compleja porque une varias tablas para obtener toda la info necesaria.
    query = text("""
        SELECT
            a.idqr_assets AS id,
            a.asset_name,
            a.asset_color,
            t.name AS item_type_name,
            ug.group_name,
            (a.qr_code_id IS NOT NULL) AS has_qr_code,
            t.can_be_container AS is_container,
            -- Subconsulta para contar cuántos ítems contiene este ítem
            (SELECT COUNT(*) FROM qr_assets AS sub WHERE sub.parent_asset_id = a.idqr_assets) AS contained_items_count,
            -- Subconsulta para obtener la URL de la imagen principal
            (SELECT att.file_url FROM asset_attachments AS att WHERE att.asset_id = a.idqr_assets AND att.attachment_type = 'asset_picture' LIMIT 1) AS image_url
        FROM
            qr_assets AS a
        JOIN
            asset_types AS t ON a.iditem_types = t.type_id
        LEFT JOIN
            user_groups AS ug ON a.group_id = ug.group_id
        WHERE
            a.users_idusers = :user_id
            AND a.status != 'DELETED'
        ORDER BY
            a.activation_date DESC
        LIMIT :limit OFFSET :offset
    """)
    
    try:
        results = db.execute(query, {"user_id": user_id, "limit": limit, "offset": offset}).mappings().all()
        
        # 4. Construir la respuesta final
        pagination_data = PaginationOut(
            current_page=page,
            has_more_pages=(offset + len(results) < total_items),
            total_items=total_items
        )
        
        response_data = AssetListResponse(
            items=results,
            pagination=pagination_data
        )
        
        return response_data

    except Exception as e:
        log_error(get_mongo_db(), "/assets", "GET", e, user_context={"user_id": user_id})
        raise HTTPException(status_code=500, detail="Error fetching assets")


@router.get("/{asset_id}", response_model=AssetDetailOut)
async def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = int(current_user.get("user_id"))

    query = text("""
        SELECT
            a.idqr_assets,
            a.asset_name,
            a.asset_color,
            a.asset_serial,
            a.asset_description,
            a.group_id,
            a.parent_asset_id,
            a.iditem_types,
            a.status,
            (SELECT att.file_url FROM asset_attachments AS att
             WHERE att.asset_id = a.idqr_assets AND att.attachment_type = 'asset_picture'
             LIMIT 1) AS image_url,
            (SELECT att.file_url FROM asset_attachments AS att
             WHERE att.asset_id = a.idqr_assets AND att.attachment_type = 'asset_document'
             LIMIT 1) AS receipt_url
        FROM qr_assets AS a
        WHERE a.idqr_assets = :asset_id AND a.users_idusers = :user_id
    """)

    row = db.execute(query, {"asset_id": asset_id, "user_id": user_id}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")

    return dict(row)


@router.put("/{asset_id}", response_model=AssetDetailOut)
async def update_asset(
    asset_id: int,
    asset_data: AssetUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    mongo_db = Depends(get_mongo_db)
):
    user_id = int(current_user.get("user_id"))

    exists = db.execute(
        text("SELECT idqr_assets FROM qr_assets WHERE idqr_assets = :asset_id AND users_idusers = :user_id"),
        {"asset_id": asset_id, "user_id": user_id}
    ).first()

    if not exists:
        raise HTTPException(status_code=404, detail="Asset not found")

    update_query = text("""
        UPDATE qr_assets
        SET asset_name        = :asset_name,
            asset_description = :desc,
            asset_color       = :color,
            asset_serial      = :serial,
            group_id          = :group_id,
            parent_asset_id   = :parent_id,
            iditem_types      = :type_id
        WHERE idqr_assets = :asset_id AND users_idusers = :user_id
    """)

    try:
        db.execute(update_query, {
            "asset_name": asset_data.asset_name,
            "desc":       asset_data.asset_description,
            "color":      asset_data.asset_color,
            "serial":     asset_data.asset_serial,
            "group_id":   asset_data.group_id,
            "parent_id":  asset_data.parent_asset_id,
            "type_id":    asset_data.iditem_types,
            "asset_id":   asset_id,
            "user_id":    user_id,
        })
        db.commit()
    except Exception as e:
        db.rollback()
        log_error(mongo_db, f"/assets/{asset_id}", "PUT", e,
                  request_payload=asset_data.dict(), user_context={"user_id": user_id})
        raise HTTPException(status_code=500, detail="Failed to update asset")

    fetch_query = text("""
        SELECT
            a.idqr_assets, a.asset_name, a.asset_color, a.asset_serial,
            a.asset_description, a.group_id, a.parent_asset_id, a.iditem_types, a.status,
            (SELECT att.file_url FROM asset_attachments AS att
             WHERE att.asset_id = a.idqr_assets AND att.attachment_type = 'asset_picture'
             LIMIT 1) AS image_url,
            (SELECT att.file_url FROM asset_attachments AS att
             WHERE att.asset_id = a.idqr_assets AND att.attachment_type = 'asset_document'
             LIMIT 1) AS receipt_url
        FROM qr_assets AS a
        WHERE a.idqr_assets = :asset_id AND a.users_idusers = :user_id
    """)
    row = db.execute(fetch_query, {"asset_id": asset_id, "user_id": user_id}).mappings().first()
    return dict(row)


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    mongo_db = Depends(get_mongo_db)
):
    user_id = int(current_user.get("user_id"))

    exists = db.execute(
        text("SELECT idqr_assets FROM qr_assets WHERE idqr_assets = :asset_id AND users_idusers = :user_id"),
        {"asset_id": asset_id, "user_id": user_id}
    ).first()

    if not exists:
        raise HTTPException(status_code=404, detail="Asset not found")

    try:
        db.execute(
            text("UPDATE qr_assets SET status = 'DELETED' WHERE idqr_assets = :asset_id AND users_idusers = :user_id"),
            {"asset_id": asset_id, "user_id": user_id}
        )
        db.commit()
    except Exception as e:
        db.rollback()
        log_error(mongo_db, f"/assets/{asset_id}", "DELETE", e, user_context={"user_id": user_id})
        raise HTTPException(status_code=500, detail="Failed to delete asset")

    return {"success": True}