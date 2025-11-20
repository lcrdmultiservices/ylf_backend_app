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
from app.api.log_otp_failure import router as log_otp_failure_router
from app.api.verify_hcaptcha import router as verify_hcaptcha_router
from app.api import login_local, register_local_personal, password_recovery, logout, session_verify 
from app.api.ui_config import router as ui_config_router
from app.routers import user_groups 
from app.api import asset_classifications
from app.api import asset_management
from slowapi import _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core import limiter 
from app.api import identifier_manager

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Manejador de Excepciones ---
@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    logger.error("--- INICIO DEL REPORTE DE EXCEPCIÓN ---")
    logger.error(f"Ruta de la solicitud: {request.url.path}")
    logger.error(f"Tipo de excepción: {type(exc).__name__}")
    
    status_code = 500
    detail = "error_server_issue"

    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        detail = exc.detail
        logger.info(f"La excepción es una HTTPException controlada. Status Code: {status_code}, Detail: '{detail}'")
    else:
        logger.error(f"La excepción es un error no controlado del servidor: {exc}", exc_info=True)

    logger.error("--- FIN DEL REPORTE DE EXCEPCIÓN ---")
    
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
    )

# --- Middleware de CORS (CORREGIDO para cookies) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ✅ Tu frontend local
    allow_credentials=True,                   # ✅ Necesario para enviar cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Inclusión de Routers ---
app.include_router(person_lookup_router, prefix="/api")
app.include_router(countries_router, prefix="/api")
app.include_router(register_local_user_router, prefix="/api")
app.include_router(terms_router, prefix="/api")
app.include_router(consents_router, prefix="/api")
app.include_router(login_local_router, prefix="/api")
app.include_router(verify_account_router, prefix="/api")
app.include_router(resend_otp_router, prefix="/api")
app.include_router(log_otp_failure_router, prefix="/api")
app.include_router(verify_hcaptcha_router, prefix="/api")
app.include_router(password_recovery.router, prefix="/api")
app.include_router(logout.router, prefix="/api")
app.include_router(session_verify.router, prefix="/api")
app.include_router(ui_config_router, prefix="/api")
app.include_router(user_groups.router, prefix="/api") 
app.include_router(asset_classifications.router, prefix="/api")
app.include_router(asset_management.router, prefix="/api")
app.include_router(identifier_manager.router, prefix="/api")
