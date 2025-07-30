import random
from datetime import datetime, timedelta, timezone

# Este archivo contendrá toda la lógica para generar y verificar OTPs.

def generate_and_store_otp(mongo_db, user_id: int, email: str, otp_context: str, lifespan_minutes: int = 10) -> str | None:
    """
    Genera un OTP de 6 dígitos, lo guarda en MongoDB y devuelve el código.
    """
    if mongo_db is None:
        print("ERROR: No se puede generar OTP, la conexión a MongoDB no está disponible.")
        return None
    
    try:
        otp_collection = mongo_db.otps
        otp_code = str(random.randint(100000, 999999))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=lifespan_minutes)

        # Log de depuración para ver el código generado en la consola del backend.
        print(f"DEBUG: Generated OTP for {email} ({otp_context}): {otp_code}")

        otp_collection.update_one(
            {"email": email, "context": otp_context},
            {
                "$set": {
                    "user_id": user_id,
                    "code": otp_code,
                    "created_at": datetime.now(timezone.utc),
                    "expires_at": expires_at,
                    "used": False
                }
            },
            upsert=True
        )
        return otp_code
    except Exception as e:
        print(f"Error al generar y guardar OTP para {email}: {e}")
        return None

def verify_otp(mongo_db, email: str, otp_code: str, otp_context: str, delete_on_verify: bool = False) -> bool:
    """
    Verifica si un OTP es válido para un email y contexto específicos.
    """
    if mongo_db is None:
        print("ERROR: No se puede verificar el OTP, la conexión a MongoDB no está disponible.")
        return False

    try:
        otp_collection = mongo_db.otps
        
        otp_data = otp_collection.find_one({
            "email": email,
            "context": otp_context
        })

        if not otp_data:
            print(f"DEBUG: OTP verification failed for {email}. Reason: No OTP found for this context.")
            return False

        is_code_valid = otp_data["code"] == otp_code
        
        # --- CORRECCIÓN ---
        # Se usa datetime.utcnow() para obtener una fecha "naive" (sin timezone)
        # y así poder compararla con la fecha "naive" que viene de MongoDB, evitando el error.
        is_expired = datetime.utcnow() > otp_data["expires_at"]

        if is_code_valid and not is_expired:
            if delete_on_verify:
                otp_collection.delete_one({"_id": otp_data["_id"]})
            return True
        else:
            # Logs de depuración para entender por qué falló la verificación.
            if is_expired:
                print(f"DEBUG: OTP verification failed for {email}. Reason: Expired.")
            elif not is_code_valid:
                print(f"DEBUG: OTP verification failed for {email}. Reason: Invalid code. Provided: {otp_code}, Stored: {otp_data['code']}")
            return False

    except Exception as e:
        print(f"Error al verificar OTP para {email}: {e}")
        return False
