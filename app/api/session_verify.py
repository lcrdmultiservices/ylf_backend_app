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