from datetime import datetime, timedelta
from typing import Optional
# --- IMPORTACIONES ACTUALIZADAS ---
from jose import JWTError, jwt, ExpiredSignatureError
from fastapi import HTTPException
from app.config import settings

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# --- FUNCIÓN MODIFICADA ---
def verify_token(token: str):
    """
    Verifica un token JWT, distinguiendo entre diferentes tipos de error.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            # Si el token es válido pero no tiene el campo 'sub'
            raise HTTPException(status_code=401, detail="invalid_token_payload")
        return {"user_id": user_id}

    except ExpiredSignatureError:
        # Error específico para tokens expirados (NORMAL)
        raise HTTPException(status_code=401, detail="token_expired")
    except JWTError:
        # Error genérico para tokens inválidos (SOSPECHOSO)
        raise HTTPException(status_code=401, detail="invalid_token")