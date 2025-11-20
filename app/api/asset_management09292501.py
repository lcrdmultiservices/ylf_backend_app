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
from app.limiter import limiter 


router = APIRouter(prefix="/assets", tags=["Asset Management"])

# --- Modelos Pydantic para la creación de activos ---
class AssetCreate(BaseModel):
    asset_name: str
    asset_description: str | None = None
    asset_color: str | None = None
    asset_serial: str | None = None
    group_id: int | None = None
    parent_asset_id: int | None = None
    item_type_id: int # El id del tipo de la tabla asset_types
    is_currently_container: bool = False

# --- Constantes de Configuración de Archivos ---
MEDIA_ROOT = "media" # Asegúrate que esta carpeta exista en la raíz de tu proyecto
os.makedirs(MEDIA_ROOT, exist_ok=True)


@router.post("/", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_asset(asset_data: AssetCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user), mongo_db = Depends(get_mongo_db)):
    user_id = int(current_user.get("user_id"))
    
    if not asset_data.asset_name.strip() or not asset_data.item_type_id:
       raise HTTPException(status_code=422, detail="Asset name and type are required")
    
    
    query = text("""
        INSERT INTO qr_assets (users_idusers, asset_name, asset_description, asset_color, asset_serial, group_id, parent_asset_id, iditem_types, is_currently_container, status, activation_date)
        VALUES (:user_id, :asset_name, :desc, :color, :serial, :group_id, :parent_id, :type_id, :is_container, 'ACTIVE', NOW())
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
            "is_container": asset_data.is_currently_container
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
    asset_id: int, 
    use: str,
    file: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user),
    mongo_db = Depends(get_mongo_db)):
    user_id = int(current_user.get("user_id"))
    
    # 1. Verificar que el asset pertenece al usuario actual (importante por seguridad)
    asset_check_query = text("SELECT idqr_assets FROM qr_assets WHERE idqr_assets = :asset_id AND users_idusers = :user_id")
    if not db.execute(asset_check_query, {"asset_id": asset_id, "user_id": user_id}).first():
        raise HTTPException(status_code=404, detail="Asset not found or permission denied")
    
    # 7. Validación de archivo con python-magic
    file_content = await file.read()
    await file.seek(0) # Rebobinar el archivo por si se necesita leer de nuevo
    
    detected_mime_type = magic.from_buffer(file_content, mime=True)
    allowed_mime_types = ['image/jpeg', 'image/png', 'application/pdf']
    
    if detected_mime_type not in allowed_mime_types:
        raise HTTPException(status_code=400, detail=f"Invalid file type detected: {detected_mime_type}. Only JPG, PNG, and PDF are allowed.")

    # 2. Guardar el archivo en el servidor con un nombre único
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(MEDIA_ROOT, unique_filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # 3. Guardar la referencia en la base de datos
    file_url = f"/{MEDIA_ROOT}/{unique_filename}" # URL relativa para acceder al archivo
    
    attachment_query = text("""
        INSERT INTO asset_attachments (asset_id, attachment_type, file_url, mime_type, original_filename, file_size_bytes)
        VALUES (:asset_id, :type, :url, :mime, :orig_name, :size)
    """)
    
    try:
        db.execute(attachment_query, {
            "asset_id": asset_id,
            "use": use,
            "url": file_url,
            "mime": file.content_type,
            "orig_name": file.filename,
            "size": file.size
        })
        db.commit()
    except Exception as e:
        db.rollback()
        os.remove(file_path) # Si falla la BD, borramos el archivo subido
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