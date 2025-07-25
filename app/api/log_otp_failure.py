from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime, timezone

from app.db.database import get_db, get_mongo_db

router = APIRouter()

class FailedAttempt(BaseModel):
    attempted_code: str
    timestamp: datetime

class LogOtpFailureRequest(BaseModel):
    user_id: int
    email: str
    otp_context: str
    failed_attempts: List[FailedAttempt]

@router.post("/log-otp-failure")
def log_otp_failure(data: LogOtpFailureRequest, request: Request, mongo_db = Depends(get_mongo_db)):
    """
    Registra en MongoDB un incidente de múltiples intentos fallidos de verificación OTP.
    """
    if mongo_db is None:
        raise HTTPException(status_code=503, detail="error_db_connection")

    try:
        failure_logs_collection = mongo_db.otp_failure_logs

        # Obtener el código OTP correcto más reciente para este usuario y contexto
        otp_collection = mongo_db.otp_codes
        correct_otp_doc = otp_collection.find_one(
            {"user_id": data.user_id, "otp_context": data.otp_context, "used": False},
            sort=[("created_at", -1)]
        )
        correct_otp_code = correct_otp_doc.get("otp_code", "UNKNOWN") if correct_otp_doc else "UNKNOWN"

        log_document = {
            "user_id": data.user_id,
            "email": data.email,
            "otp_context": data.otp_context,
            "correct_otp_code": correct_otp_code,
            "failed_attempts": [attempt.dict() for attempt in data.failed_attempts],
            "incident_reported_at": datetime.now(timezone.utc),
            "user_context": {
                "ip_address": request.client.host if request.client else "N/A",
                "user_agent": request.headers.get('user-agent', 'Unknown')
            }
        }

        failure_logs_collection.insert_one(log_document)
        
        return {"status": "success", "message": "Failure logged successfully."}

    except Exception as e:
        # No queremos que un fallo en el logging impida al usuario obtener ayuda.
        # Lo registramos en la consola y devolvemos éxito de todas formas.
        print(f"CRITICAL: Could not log OTP failure to MongoDB. Error: {e}")
        return {"status": "success", "message": "Failure logging failed, but proceeding."}
