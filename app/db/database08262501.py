from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pymongo import MongoClient
import redis
from typing import Generator
from fastapi import HTTPException

# Importar nuestra nueva configuración centralizada
from app.config import settings

# --- 1. Configuración de la Base de Datos SQL ---
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 2. Configuración de la Base de Datos NoSQL (MongoDB) ---
mongo_client = None
try:
    mongo_client = MongoClient(settings.MONGO_URL)
    mongo_client.admin.command('ping')
    print("Conexión a MongoDB establecida exitosamente.")
except Exception as e:
    print(f"Error de conexión a MongoDB: {e}")
    mongo_client = None

# --- 3. NUEVO: Configuración de Redis ---
redis_client = None
try:
    redis_client = redis.Redis(
    host=settings.REDIS_HOST, 
    port=settings.REDIS_PORT, 
    password=settings.REDIS_PASSWORD, # <-- AÑADIR ESTE PARÁMETRO
    db=0, 
    decode_responses=True
    )
    redis_client.ping()
    print("Conexión a Redis establecida exitosamente.")
except Exception as e:
    print(f"Error de conexión a Redis: {e}")
    redis_client = None

# --- 4. Funciones de Dependencia para FastAPI ---

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_mongo_db():
    if mongo_client is not None:
        try:
            yield mongo_client[settings.MONGO_DB_NAME]
        except Exception as e:
            print(f"No se pudo obtener la base de datos de MongoDB: {e}")
            raise HTTPException(status_code=500, detail="Could not connect to logging service.")
    else:
        raise HTTPException(status_code=500, detail="Logging service is not configured.")

def get_redis_client():
    if redis_client is not None:
        yield redis_client
    else:
        raise HTTPException(status_code=500, detail="Cache service is not configured.")
