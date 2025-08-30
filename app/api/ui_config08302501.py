# en app/api/ui_config.py
from fastapi import APIRouter, Depends, HTTPException
from app.db.database import get_mongo_db

router = APIRouter(prefix="/ui", tags=["UI Configuration"])

@router.get("/menu-config/{user_type_id}")
async def get_menu_config(user_type_id: int, mongo_db = Depends(get_mongo_db)):
    """
    Obtiene la configuración de la interfaz de usuario (menús y rutas)
    basada en el tipo de usuario.
    """
    if mongo_db is None:
        raise HTTPException(status_code=503, detail="error_mongo_unavailable")
    
    try:
        # Aquí buscarías el config por el ID, ej: 'personal_standard_ui_v1'
        # Por ahora, lo haré simple y buscaré el primero que encuentre.
        # En una versión real, podrías tener configs para admin, personal, etc.
        config_document = mongo_db.ui_configurations.find_one({"_id": "personal_standard_ui_v1"})
        
        if not config_document:
            raise HTTPException(status_code=404, detail="error_ui_config_not_found")
        
        return config_document

    except Exception as e:
        # Aquí podrías loguear el error
        raise HTTPException(status_code=500, detail="error_fetching_ui_config")