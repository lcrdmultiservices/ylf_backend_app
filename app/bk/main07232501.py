from fastapi import FastAPI
from app.api.person_lookup import router as person_lookup_router
from app.api.countries import router as countries_router
from app.api.register_local_personal import router as register_local_user_router
from app.api.terms import router as terms_router
from fastapi.middleware.cors import CORSMiddleware
# --- CORRECCIÓN: Se cambia 'consents' por 'consent' para que coincida con el nombre del archivo ---
from app.api.consent import router as consents_router
from app.api.login_local import router as login_local_router
from app.api.verify_account import router as verify_account_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Origen de tu frontend
    allow_credentials=False,
    allow_methods=["*"],  # Permitir todos los métodos: GET, POST, etc.
    allow_headers=["*"],  # Permitir todos los encabezados (como Content-Type)
)

# Incluir los routers
app.include_router(person_lookup_router, prefix="/api")
app.include_router(countries_router, prefix="/api")
app.include_router(register_local_user_router, prefix="/api")
app.include_router(terms_router, prefix="/api")
app.include_router(consents_router, prefix="/api")
app.include_router(login_local_router, prefix="/api")
app.include_router(verify_account_router, prefix="/api")
