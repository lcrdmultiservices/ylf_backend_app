import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv
from typing import Generator
from fastapi import HTTPException

load_dotenv()

# --- 1. Configuración de la Base de Datos SQL ---
DB_USER = os.getenv("DB_USER", "masterlcr")
DB_PASS = os.getenv("DB_PASS", "LcRd1804")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "ylf_db")

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# --- 2. Configuración de la Base de Datos NoSQL (MongoDB) ---
# Se utiliza la cadena de conexión que proporcionaste.
MONGO_DATABASE_URL = "mongodb://masterlcr:LcRd%401804@localhost:27017/ylf_db?authSource=admin"
MONGO_DATABASE_NAME = "ylf_db"

mongo_client = None
if MONGO_DATABASE_URL is not None:
    try:
        mongo_client = MongoClient(MONGO_DATABASE_URL)
        mongo_client.admin.command('ping')
        print("Conexión a MongoDB establecida exitosamente.")
    except ConnectionFailure as e:
        print(f"Error de conexión a MongoDB: {e}")
        mongo_client = None
    except Exception as e:
        print(f"Ocurrió un error inesperado al conectar con MongoDB: {e}")
        mongo_client = None
else:
    print("Advertencia: La variable de entorno MONGO_URL no está definida.")


# --- 3. Funciones de Dependencia para FastAPI ---

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_mongo_db():
    """
    Dependencia de FastAPI para obtener una instancia de la base de datos MongoDB.
    """
    # --- CORRECCIÓN PRINCIPAL: Se cambia 'if mongo_client:' por 'if mongo_client is not None:' ---
    if mongo_client is not None:
        try:
            yield mongo_client[MONGO_DATABASE_NAME]
        except Exception as e:
            print(f"No se pudo obtener la base de datos de MongoDB: {e}")
            raise HTTPException(status_code=500, detail="Could not connect to logging service.")
    else:
        print("El cliente de MongoDB no está disponible.")
        raise HTTPException(status_code=500, detail="Logging service is not configured.")
