from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from app.config import settings # Importamos nuestra configuración

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Crea un nuevo token de acceso.
    
    :param data: Datos a codificar en el token (payload).
    :param expires_delta: Duración opcional del token.
    :return: El token JWT codificado como una cadena.
    """
    to_encode = data.copy()
    
    # Establece el tiempo de expiración
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Si no se especifica, usa una duración por defecto (ej. 15 minutos)
        expire = datetime.utcnow() + timedelta(minutes=15)
        
    to_encode.update({"exp": expire})
    
    # Codifica el token con la clave secreta y el algoritmo
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str, credentials_exception):
    """
    Verifica un token JWT.
    
    :param token: El token a verificar.
    :param credentials_exception: La excepción a lanzar si la validación falla.
    :return: Los datos (payload) del token si es válido.
    """
    try:
        # Decodifica el token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Extrae el ID del usuario del 'subject' del token
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
        return {"user_id": user_id}

    except JWTError:
        # Si hay cualquier error con el token (expirado, inválido, etc.)
        raise credentials_exception