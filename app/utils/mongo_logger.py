import traceback
from datetime import datetime, timezone
from fastapi import HTTPException

# Esta función no se conecta a la base de datos, solo la utiliza.
# La conexión es gestionada por database.py e inyectada por FastAPI.

def log_error(mongo_db, endpoint: str, method: str, error: Exception, request_payload: dict = None, user_context: dict = None):
    """
    Registra un error en la colección 'error_logs' de MongoDB.
    
    Args:
        mongo_db: El objeto de la base de datos de MongoDB inyectado por FastAPI.
        endpoint (str): El endpoint donde ocurrió el error.
        method (str): El método HTTP.
        error (Exception): El objeto de la excepción capturada.
        request_payload (dict, optional): El cuerpo de la solicitud que causó el error.
        user_context (dict, optional): Información adicional como la IP del usuario.
    """
    # --- CORRECCIÓN CLAVE ---
    # Se cambia la comprobación 'if not mongo_db' por 'if mongo_db is None'.
    # Este es el cambio que soluciona el error que estás viendo.
    if mongo_db is None:
        print("CRITICAL: No se puede registrar el error porque la conexión a MongoDB no está disponible.")
        return

    try:
        error_log_collection = mongo_db.error_logs
        
        # Extraer el mensaje de error de forma segura
        if isinstance(error, HTTPException):
            error_message = error.detail
        else:
            error_message = str(error)

        error_document = {
            "timestamp": datetime.now(timezone.utc),
            "endpoint": endpoint,
            "method": method,
            "error_type": type(error).__name__,
            "error_message": error_message,
            "traceback": traceback.format_exc(),
            "request_payload": request_payload or {},
            "user_context": user_context or {}
        }
        
        error_log_collection.insert_one(error_document)
        print(f"Error registrado exitosamente en MongoDB para el endpoint {endpoint}.")

    except Exception as e:
        # Si el propio logging falla, lo imprimimos en la consola para no causar un bucle de errores.
        print(f"CRITICAL: Fallo al registrar un error en MongoDB. Error original: {error}. Error de logging: {e}")

