# app/auth/security.py

from fastapi import Depends, Request, HTTPException, status
from typing import Optional

# Importamos las funciones que ya tienes y que funcionan bien
from app.utils.jwt_handler import verify_token
from app.api.session_verify import get_session_token

async def get_current_user(request: Request, token: Optional[str] = Depends(get_session_token)):
    """
    Esta es la dependencia que protegerá tus endpoints.
    Obtiene el token y usa tu función verify_token para validarlo.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Simplemente llamamos a tu función verify_token.
    # Si el token es inválido o ha expirado, esa función ya
    # se encarga de lanzar la HTTPException correcta.
    return verify_token(token)