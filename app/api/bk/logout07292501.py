from fastapi import APIRouter, Response, Request
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix="/logout",
    tags=["Authentication"]
)

@router.post("", status_code=200)
async def logout_user(request: Request, response: Response):
    """
    Cierra la sesión del usuario eliminando la cookie de sesión.
    """
    # --- Verifica si la cookie fue recibida ---
    print("DEBUG COOKIE RECIBIDA:", request.cookies)

    # --- Elimina la cookie asegurando coincidencia de atributos ---
    response.delete_cookie(
        key="session_token",
        path='/',           # ✅ Igual que en set_cookie
        samesite='lax'      # ✅ CRÍTICO: debe coincidir con login
    )

    print("DEBUG: session_token marcada para eliminar")

    return JSONResponse(content={"status": "success", "detail": "Logged out successfully"})
