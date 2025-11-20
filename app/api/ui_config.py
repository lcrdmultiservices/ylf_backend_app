from fastapi import APIRouter, Depends, HTTPException
from app.db.database import get_mongo_db
from bson import ObjectId

router = APIRouter(prefix="/ui", tags=["UI Configuration"])

def serialize_mongo_document(doc):
    if doc and "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc

@router.get("/menu-config/{user_type_id}")
async def get_menu_config(user_type_id: int, mongo_db = Depends(get_mongo_db)):
    """
    Obtiene la configuración de la interfaz de usuario (menús y rutas)
    basada en el tipo de usuario.
    """
    if mongo_db is None:
        raise HTTPException(status_code=503, detail="error_mongo_unavailable")
    
    try:
        # --- CORRECCIÓN: Usar el nombre de colección correcto ---
        config_document = mongo_db.ui_structures.find_one({"_id": "personal_standard_ui_v1"})
        
        if not config_document:
            raise HTTPException(status_code=404, detail="error_ui_config_not_found")
        
        return [serialize_mongo_document(config_document)]

    except Exception as e:
        print(f"ERROR fetching menu config: {e}") 
        raise HTTPException(status_code=500, detail="error_fetching_ui_config")