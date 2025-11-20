# app/auth/security.py

from fastapi import Depends, Request, HTTPException, status
from typing import Optional

# Reutilizamos las mismas funciones que ya tienes
from app.utils.jwt_handler import verify_token
from app.api.session_verify import get_session_token 

# --- LA DEPENDENCIA REUTILIZABLE ---
async def get_current_user(request: Request, token: Optional[str] = Depends(get_session_token)):
    """
    Esta es la dependencia que protegerá tus endpoints.
    Verifica el token de la cookie y devuelve el payload del usuario si es válido.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Usamos la misma lógica de verificación que ya tenías
        payload = verify_token(token)
        # Devolvemos el payload completo (que contiene user_id, etc.)
        return payload
    except HTTPException as e:
        # Si el token es inválido, se relanza la excepción
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )