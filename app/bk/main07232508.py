from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

# Importaciones de tus routers
from app.api.person_lookup import router as person_lookup_router
from app.api.countries import router as countries_router
from app.api.register_local_personal import router as register_local_user_router
from app.api.terms import router as terms_router
from app.api.consent import router as consents_router
from app.api.login_local import router as login_local_router
from app.api.verify_account import router as verify_account_router
from app.api.resend_otp import router as resend_otp_router

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- MODIFICADO: Manejador de Excepciones con Logging Detallado ---
# Este manejador universal nos ayudará a rastrear exactamente qué está pasando.
@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    # Log para cualquier excepción que ocurra en la aplicación
    logger.error("--- INICIO DEL REPORTE DE EXCEPCIÓN ---")
    logger.error(f"Ruta de la solicitud: {request.url.path}")
    logger.error(f"Tipo de excepción: {type(exc).__name__}")
    
    status_code = 500
    detail = "error_server_issue"

    # Si la excepción es una HTTPException, usamos su información específica.
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        detail = exc.detail
        logger.info(f"La excepción es una HTTPException controlada. Status Code: {status_code}, Detail: '{detail}'")
    else:
        # Si es cualquier otro tipo de error, lo tratamos como un 500 y logueamos el traceback completo.
        logger.error(f"La excepción es un error no controlado del servidor: {exc}", exc_info=True)

    logger.error("--- FIN DEL REPORTE DE EXCEPCIÓN ---")
    
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
    )


# --- Middleware de CORS (sin cambios) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Inclusión de Routers (sin cambios) ---
app.include_router(person_lookup_router, prefix="/api")
app.include_router(countries_router, prefix="/api")
app.include_router(register_local_user_router, prefix="/api")
app.include_router(terms_router, prefix="/api")
app.include_router(consents_router, prefix="/api")
app.include_router(login_local_router, prefix="/api")
app.include_router(verify_account_router, prefix="/api")
app.include_router(resend_otp_router, prefix="/api")
