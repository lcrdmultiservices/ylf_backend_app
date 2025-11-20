from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import get_db
from app.auth.security import get_current_user

router = APIRouter(
    prefix="/asset-classifications", 
    tags=["Asset Classifications"]
)

# --- Modelos Pydantic (Sin cambios) ---
class ItemTypeOut(BaseModel):
    id: int
    name: str
    key: str
    can_be_container: bool

class AssetCategoryOut(BaseModel):
    id: int
    name: str
    key: str
    icon: str | None
    types: List[ItemTypeOut]

# --- Endpoint ---

@router.get("/", response_model=List[AssetCategoryOut])
async def get_all_classifications(
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    # --- CONSULTA SIMPLIFICADA PARA EL MVP ---
    # Se han eliminado los JOINs con las tablas de tipo de usuario.
    # Ahora solo une las categorías con sus tipos de activos.
    query = text("""
        SELECT 
            c.category_id, 
            c.name as category_name, 
            c.translation_key as category_key,
            c.icon_name as category_icon,
            t.type_id,
            t.name as type_name,
            t.translation_key as type_key,
            t.can_be_container
        FROM asset_categories c
        JOIN asset_types t ON c.category_id = t.id_category
        ORDER BY
            CASE c.sort_order
                WHEN 'always_first' THEN 1
                WHEN 'alpha_A' THEN 2
                WHEN 'alpha_Z' THEN 3
                ELSE 4
            END, c.name,
            CASE t.sort_order
                WHEN 'always_first' THEN 1
                WHEN 'alpha_A' THEN 2
                WHEN 'alpha_Z' THEN 3
                ELSE 4
            END, t.name
    """)
    
    try:
        # La ejecución ya no necesita pasar el parámetro 'user_account_type'
        result = db.execute(query).fetchall()
    except Exception as e:
        # Aquí podrías usar tu mongo_logger si la consulta falla
        # log_error(...)
        raise HTTPException(status_code=500, detail="Error fetching asset classifications")

    # El resto de la lógica para estructurar el JSON no necesita cambios.
    categories_map = {}
    for row in result:
        if row.category_id not in categories_map:
            categories_map[row.category_id] = {
                "id": row.category_id, "name": row.category_name,
                "key": row.category_key, "icon": row.category_icon,
                "types": []
            }
        
        if row.type_id:
            categories_map[row.category_id]["types"].append({
                "id": row.type_id, "name": row.type_name,
                "key": row.type_key, "can_be_container": row.can_be_container
            })
            
    return list(categories_map.values())