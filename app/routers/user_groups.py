from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
# ✅ CAMBIO: Importamos la dependencia para SQL y quitamos la de Mongo
from app.db.database import get_db
from app.auth.security import get_current_user 
from app.core import NoTrailingSlashRouter

router = NoTrailingSlashRouter(prefix="/user-groups", tags=["User Groups"])

# --- Modelos Pydantic (No cambian, pero group_id será un int) ---

class GroupBase(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=100)
    parent_group_id: Optional[int] = None

class GroupCreate(GroupBase):
    pass

class GroupUpdate(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)

class GroupOut(GroupBase):
    group_id: int
    owner_user_id: int
    
# --- Endpoints ---

@router.get("/", response_model=List[GroupOut])
# ✅ CAMBIO: Usamos la dependencia de base de datos SQL
async def get_user_groups(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id_str = current_user.get("user_id")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="User ID not found in token")
    
    try:
        user_id_int = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid User ID format in token")

    # ✅ CAMBIO: Escribimos la consulta en SQL
    query = text("SELECT group_id, owner_user_id, group_name, parent_group_id FROM user_groups WHERE owner_user_id = :user_id")
    
    # ✅ CAMBIO: Ejecutamos la consulta SQL
    result = db.execute(query, {"user_id": user_id_int})
    groups_from_db = result.fetchall()
    
    # Mapeamos los resultados a nuestro modelo Pydantic
    groups_list = []
    for group in groups_from_db:
        groups_list.append(GroupOut(
            group_id=group.group_id,
            owner_user_id=group.owner_user_id,
            group_name=group.group_name,
            parent_group_id=group.parent_group_id
        ))
        
    return groups_list

@router.post("/", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
async def create_user_group(group: GroupCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id_int = int(current_user.get("user_id"))

    # ✅ CAMBIO: Escribimos la consulta de inserción en SQL
    query = text("""
        INSERT INTO user_groups (owner_user_id, group_name, parent_group_id) 
        VALUES (:owner_user_id, :group_name, :parent_group_id)
    """)
    
    try:
        result = db.execute(query, {
            "owner_user_id": user_id_int,
            "group_name": group.group_name,
            "parent_group_id": group.parent_group_id
        })
        db.commit()

        # Obtenemos el ID del grupo recién creado
        new_group_id = result.lastrowid
        
        # Consultamos el grupo recién creado para devolverlo
        select_query = text("SELECT * FROM user_groups WHERE group_id= :group_id")
        created_group = db.execute(select_query, {"group_id": new_group_id}).first()

        return GroupOut(
            group_id=created_group.group_id,
            owner_user_id=created_group.owner_user_id,
            group_name=created_group.group_name,
            parent_group_id=created_group.parent_group_id
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="group_name_already_exists")    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create group")

@router.put("/{group_id}", response_model=GroupOut)
async def update_user_group(group_id: int, group_update: GroupUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if not group_update.group_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="group_name_cannot_be_empty")
    user_id_int = int(current_user.get("user_id"))

    select_query = text("SELECT * FROM user_groups WHERE group_id = :group_id AND owner_user_id = :user_id")
    group_to_update = db.execute(select_query, {"group_id": group_id, "user_id": user_id_int}).first()

    if not group_to_update:
        raise HTTPException(status_code=404, detail="Group not found or you don't have permission to edit it")
    
    if group_to_update.parent_group_id is None:
        raise HTTPException(status_code=403, detail="The default root group cannot be renamed")

    try:
        update_query = text("UPDATE user_groups SET group_name = :new_name WHERE group_id = :group_id")
        db.execute(update_query, {"new_name": group_update.group_name, "group_id": group_id})
        db.commit()

        updated_group = db.execute(select_query, {"group_id": group_id, "user_id": user_id_int}).first()
        return GroupOut(
            group_id=updated_group.group_id,
            owner_user_id=updated_group.owner_user_id,
            group_name=updated_group.group_name,
            parent_group_id=updated_group.parent_group_id
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="group_name_already_exists")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update group")    

@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_group(group_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id_int = int(current_user.get("user_id"))

    # TODO: Implementar una lógica más robusta para borrado en cascada si es necesario
    # Por ahora, borramos los hijos directos y luego el padre.
    
    try:
        # ✅ CAMBIO: Lógica de borrado en SQL
        delete_children_query = text("DELETE FROM user_groups WHERE parent_group_id = :group_id AND owner_user_id = :owner_user_id")
        db.execute(delete_children_query, {"group_id": group_id, "owner_user_id": user_id_int})

        delete_query = text("DELETE FROM user_groups WHERE group_id = :group_id AND owner_user_id = :owner_user_id")
        result = db.execute(delete_query, {"group_id": group_id, "owner_user_id": user_id_int})

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Group not found or you don't have permission to delete it")

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete group")
    
    return