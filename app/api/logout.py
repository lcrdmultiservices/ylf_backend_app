from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix="/logout",
    tags=["Authentication"]
)

@router.post("", status_code=200)
async def logout_user(request: Request):
    """
    Cierra la sesión del usuario eliminando la cookie de sesión.
    """
    # 1. Crea el objeto de respuesta JSON que se enviará.
    response = JSONResponse(content={"status": "success", "detail": "Logged out successfully"})

    # 2. Llama a delete_cookie sobre ESE MISMO objeto de respuesta.
    response.delete_cookie(
        key="session_token",
        path='/',
        samesite='lax'
    )

    # 3. Devuelve la respuesta ya modificada.
    return response