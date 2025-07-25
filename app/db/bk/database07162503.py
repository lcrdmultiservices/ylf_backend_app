import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv
from typing import Generator
from fastapi import HTTPException

# Cargar variables de entorno desde el archivo .env al inicio
load_dotenv()

# --- 1. Configuración de la Base de Datos SQL (Tu código original) ---
DB_USER = os.getenv("DB_USER", "masterlcr")
DB_PASS = os.getenv("DB_PASS", "LcRd1804")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "ylf_db")

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# --- 2. NUEVO: Configuración de la Base de Datos NoSQL (MongoDB) ---
# MONGO_DATABASE_URL = os.getenv("MONGO_URL")
# MONGO_DATABASE_NAME = os.getenv("MONGO_DB_NAME", "ylf_logs")

MONGO_DATABASE_URL = "mongodb://masterlcr:LcRd%401804@localhost:27017/ylf_db?authSource=admin"
MONGO_DATABASE_NAME = "ylf_db"

mongo_client = None
if MONGO_DATABASE_URL:
    try:
        mongo_client = MongoClient(MONGO_DATABASE_URL)
        # Verificar la conexión
        mongo_client.admin.command('ping')
        print("Conexión a MongoDB establecida exitosamente.")
    except ConnectionFailure as e:
        print(f"Error de conexión a MongoDB: {e}")
        mongo_client = None
    except Exception as e:
        print(f"Ocurrió un error inesperado al conectar con MongoDB: {e}")
        mongo_client = None
else:
    print("Advertencia: La variable de entorno MONGO_URL no está definida. La conexión a MongoDB no se establecerá.")


# --- 3. Funciones de Dependencia para FastAPI ---

def get_db() -> Generator[Session, None, None]:
    """
    Dependencia de FastAPI para obtener una sesión de base de datos SQL.
    (Tu función original, con una pequeña corrección de sintaxis)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_mongo_db():
    """
    NUEVA DEPENDENCIA: Dependencia de FastAPI para obtener una instancia de la base de datos MongoDB.
    """
    if mongo_client:
        try:
            # Devuelve el objeto de la base de datos específica (ej. 'ylf_logs')
            yield mongo_client[MONGO_DATABASE_NAME]
        except Exception as e:
            print(f"No se pudo obtener la base de datos de MongoDB: {e}")
            raise HTTPException(status_code=500, detail="Could not connect to logging service.")
    else:
        print("El cliente de MongoDB no está disponible.")
        raise HTTPException(status_code=500, detail="Logging service is not configured.")
