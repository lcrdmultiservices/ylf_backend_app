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
    # Elimina la cookie asegurando que los atributos coincidan con los de la creación
    response.delete_cookie(
        key="session_token",
        path='/',
        samesite='lax'
    )

    return JSONResponse(content={"status": "success", "detail": "Logged out successfully"})