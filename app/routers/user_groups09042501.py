from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from typing import List, Optional
from pydantic import BaseModel, Field

from app.db.database import get_mongo_db
# Asumimos que tienes un sistema para obtener el usuario autenticado
from app.auth.security import get_current_user 
from bson import ObjectId

router = APIRouter(prefix="/user-groups", tags=["User Groups"])

# --- Modelos Pydantic para validación de datos ---

class GroupBase(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=100)
    parent_group_id: Optional[str] = None

class GroupCreate(GroupBase):
    pass

class GroupOut(GroupBase):
    group_id: str
    owner_user_id: str
    
# --- Endpoints ---

@router.get("/", response_model=List[GroupOut])
async def get_user_groups(db: Database = Depends(get_mongo_db), current_user: dict = Depends(get_current_user)):
    """
    Obtiene todos los grupos de organización para el usuario autenticado.
    """
    user_id = current_user.get("user_id")
    print(f"--- BUSCANDO GRUPOS PARA EL USER_ID: '{user_id}' (Tipo: {type(user_id)}) ---")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found in token")
    
    # Buscamos todos los documentos que pertenecen al usuario
    groups_cursor = db.user_groups.find({"owner_user_id": user_id})
    
    # Los convertimos a un formato compatible con Pydantic
    groups_list = []
    for group in groups_cursor:
        groups_list.append(GroupOut(
            group_id=str(group["_id"]),
            owner_user_id=group["owner_user_id"],
            group_name=group["group_name"],
            parent_group_id=group.get("parent_group_id")
        ))
        
    return groups_list

@router.post("/", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
async def create_user_group(group: GroupCreate, db: Database = Depends(get_mongo_db), current_user: dict = Depends(get_current_user)):
    """
    Crea un nuevo grupo para el usuario autenticado.
    """
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found in token")
    
    
    new_group_data = group.dict()
    new_group_data["owner_user_id"] = user_id
    
    # Insertamos el nuevo grupo en la colección
    result = db.user_groups.insert_one(new_group_data)
    created_group = db.user_groups.find_one({"_id": result.inserted_id})
    
    return GroupOut(
        group_id=str(created_group["_id"]),
        **created_group
    )

@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_group(group_id: str, db: Database = Depends(get_mongo_db), current_user: dict = Depends(get_current_user)):
    """
    Elimina un grupo de un usuario.
    TODO: Implementar lógica de borrado en cascada para los sub-grupos.
    """
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found in token")

    
    # Primero, verificamos que el grupo exista y pertenezca al usuario
    group_to_delete = db.user_groups.find_one({"_id": ObjectId(group_id), "owner_user_id": user_id})
    if not group_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found or you don't have permission to delete it")
        
    # Eliminamos el grupo
    db.user_groups.delete_one({"_id": ObjectId(group_id)})
    
    # Nota: Aquí deberías considerar qué hacer con los grupos hijos.
    # Una opción es eliminarlos también (borrado en cascada).
    db.user_groups.delete_many({"parent_group_id": group_id, "owner_user_id": user_id})
    
    return