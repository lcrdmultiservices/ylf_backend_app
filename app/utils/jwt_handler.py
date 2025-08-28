# en app/utils/jwt_handler.py

from datetime import datetime, timedelta
from typing import Optional
# IMPORTACIONES NECESARIAS PARA LA VERSIÓN FINAL
from jose import JWTError, jwt, ExpiredSignatureError
from fastapi import HTTPException
from app.config import settings

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Crea un nuevo token de acceso.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# --- ESTA ES LA FUNCIÓN CORRECTA Y FINAL ---
def verify_token(token: str):
    """
    Verifica un token JWT. AHORA SOLO ACEPTA 1 ARGUMENTO: el token.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            # Lanza la excepción por sí misma
            raise HTTPException(status_code=401, detail="invalid_token_payload")
        return {"user_id": user_id}
    except ExpiredSignatureError:
        # Distingue un token expirado
        raise HTTPException(status_code=401, detail="token_expired")
    except JWTError:
        # Distingue un token inválido por otras razones
        raise HTTPException(status_code=401, detail="invalid_token")