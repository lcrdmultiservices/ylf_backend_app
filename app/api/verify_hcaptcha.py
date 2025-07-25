import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import settings

router = APIRouter()

class HCaptchaRequest(BaseModel):
    token: str

@router.post("/verify-hcaptcha")
async def verify_hcaptcha(data: HCaptchaRequest):
    """
    Verifica un token de hCaptcha con el servidor de hCaptcha.
    """
    if not settings.HCAPTCHA_SECRET_KEY:
        raise HTTPException(status_code=500, detail="hCaptcha secret key not configured.")

    payload = {
        'secret': settings.HCAPTCHA_SECRET_KEY,
        'response': data.token
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("https://api.hcaptcha.com/siteverify", data=payload)
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return {"status": "success", "message": "hCaptcha verification successful."}
            else:
                # Los 'error-codes' pueden ser útiles para depurar
                error_codes = result.get('error-codes', [])
                raise HTTPException(status_code=400, detail=f"hCaptcha verification failed: {error_codes}")

        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Could not connect to hCaptcha service: {e}")