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
    # La lógica para obtener el tipo de cuenta del usuario iría aquí
    # Por ahora, para el MVP, lo dejamos fijo en 'personal'
    user_account_type = 'personal' # Este valor vendrá del token en el futuro

    # --- CORRECCIÓN: La consulta ahora usa 'asset_types' ---
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
        JOIN asset_types t ON c.category_id = t.category_id
        JOIN asset_type_user_type_link l ON t.type_id = l.asset_type_id
        JOIN user_type ut ON l.account_type_id = ut.iduser_type
        WHERE ut.name = :user_account_type
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
        result = db.execute(query, {"user_account_type": user_account_type}).fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error fetching asset classifications")

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