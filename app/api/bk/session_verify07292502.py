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
    Verifica si el token JWT en la cookie del usuario es válido,
    revisando su firma y tiempo de expiración.
    """
    if not token:
        # Si no hay cookie/token, no hay sesión activa.
        print("DEBUG: No se encontró una sesión válida.")
        raise HTTPException(status_code=401, detail="No active session found.")

    # Define la excepción que se lanzará si la validación del token falla.
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Llama a nuestra función para verificar el token.
        # Esta se encarga de decodificar y validar firma/expiración.
        payload = verify_token(token, credentials_exception)
        
        print(f"DEBUG: Token JWT verificado con éxito. Payload: {payload}")
        # Si la función no lanza una excepción, el token es válido.
        return {"status": "success", "detail": "Session is valid.", "user_id": payload.get("user_id")}

    except HTTPException as e:
        # Capturamos la excepción que nuestra función pudo haber lanzado
        # para poder imprimir un mensaje de depuración antes de enviarla al cliente.
        print(f"DEBUG: Falló la validación del token. Razón: {e.detail}")
        raise e