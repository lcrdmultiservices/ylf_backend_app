from fastapi import FastAPI
from app.api.person_lookup import router as person_lookup_router
from app.api.countries import router as countries_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Origen de tu frontend
    allow_credentials=False,
    allow_methods=["*"],  # Permitir todos los métodos: GET, POST, etc.
    allow_headers=["*"],  # Permitir todos los encabezados (como Content-Type)
)
# Incluir el router principal
app.include_router(person_lookup_router)
app.include_router(countries_router, prefix="/api")
