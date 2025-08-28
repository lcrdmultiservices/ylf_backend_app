# en app/api/session_verify.py
from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Optional
from app.utils.jwt_handler import verify_token
from app.db.database import get_mongo_db
from app.utils.mongo_logger import log_error

router = APIRouter(prefix="/session", tags=["Session"])

def get_session_token(request: Request) -> Optional[str]:
    return request.cookies.get("session_token")

@router.get("/verify")
async def verify_session(request: Request, token: Optional[str] = Depends(get_session_token), mongo_db = Depends(get_mongo_db)):
    if not token:
        raise HTTPException(status_code=401, detail="no_active_session_found")

    try:
        payload = verify_token(token)
        return {"status": "success", "detail": "Session is valid.", "user_id": payload.get("user_id")}
    except HTTPException as e:
        if e.detail == "invalid_token" or e.detail == "invalid_token_payload":
            log_error(db=mongo_db, endpoint="/session/verify", method="GET", error=e, request_data={"token_used": token}, user_context={"client_host": request.client.host})
        raise e