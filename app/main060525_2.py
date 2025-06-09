from fastapi import FastAPI
from app.api.person_lookup import router as person_lookup_router

app = FastAPI()

# Incluir el router principal
app.include_router(person_lookup_router)