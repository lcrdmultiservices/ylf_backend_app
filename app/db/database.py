from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Cargar parámetros desde variables de entorno (o usa valores por defecto)
DB_USER = os.getenv("DB_USER", "masterlcr")
DB_PASS = os.getenv("DB_PASS", "LcRd1804")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "ylf_db")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Crear el motor SQLAlchemy
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Crear SessionLocal para usar en los endpoints
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


from sqlalchemy.orm import Session
from typing import Generator

# Función de dependencia para obtener la sesión de la base de datos
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
