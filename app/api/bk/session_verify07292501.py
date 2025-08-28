from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Optional

router = APIRouter(
    prefix="/session",
    tags=["Session"]
)

# Una dependencia simple para extraer la cookie de la solicitud.
def get_session_token(request: Request) -> Optional[str]:
    return request.cookies.get("session_token")

@router.get("/verify")
async def verify_session(token: Optional[str] = Depends(get_session_token)):
    """
    Verifica si el usuario tiene una cookie de sesión válida.
    En una aplicación real, esto implicaría decodificar y validar un JWT.
    Por ahora, solo comprobamos si nuestro token simulado existe.
    """
    # Comprobamos si el token existe y tiene el formato esperado.
    if token and token.startswith("simulated_jwt_token_for_user_"):
        # Si es válido, devolvemos éxito.
        print(f"DEBUG: Sesión válida encontrada con el token: {token}")
        return {"status": "success", "detail": "Session is valid."}
    
    # Si no hay token o no es válido, se lanza una excepción que el frontend interpretará.
    print("DEBUG: No se encontró una sesión válida.")
    raise HTTPException(status_code=401, detail="No active session found.")
    
    from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Optional

# --- NUEVA IMPORTACIÓN ---
from app.utils.jwt_handler import verify_token

router = APIRouter(
    prefix="/session",
    tags=["Session"]
)

def get_session_token(request: Request) -> Optional[str]:
    """Extrae la cookie de sesión de la solicitud."""
    return request.cookies.get("session_token")

@router.get("/verify")
async def verify_session(token: Optional[str] = Depends(get_session_token)):
    """
    Verifica si el token JWT en la cookie del usuario es válido.
    """
    if not token:
        # Si no hay cookie/token, no hay sesión activa.
        raise HTTPException(status_code=401, detail="No active session found.")

    # Define la excepción que se lanzará si la validación del token falla.
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Llama a nuestra función para verificar el token.
    # Esta función se encargará de decodificar y validar firma/expiración.
    # Si falla, lanzará la 'credentials_exception' que le pasamos.
    payload = verify_token(token, credentials_exception)
    
    # Si la función no lanza una excepción, el token es válido.
    return {"status": "success", "detail": "Session is valid.", "user_id": payload.get("user_id")}