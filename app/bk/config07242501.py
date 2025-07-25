import os
from dotenv import load_dotenv
# --- CORRECCIÓN: Importar 'Optional' desde el módulo 'typing' ---
from typing import Optional

# Cargar variables de entorno desde el archivo .env
load_dotenv()

class Settings:
    # Configuración de la Base de Datos
    DB_USER: str = os.getenv("DB_USER", "masterlcr")
    DB_PASS: str = os.getenv("DB_PASS", "LcRd1804")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "3306")
    DB_NAME: str = os.getenv("DB_NAME", "ylf_db")
    DATABASE_URL: str = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # Configuración de MongoDB
    MONGO_URL: str = os.getenv("MONGO_URL", "mongodb://masterlcr:LcRd%401804@localhost:27017/ylf_db?authSource=admin")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "ylf_db")

    # Configuración de Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")

    # Configuración de Mailgun
    MAILGUN_API_KEY: str = os.getenv("MAILGUN_API_KEY")
    MAILGUN_DOMAIN: str = os.getenv("MAILGUN_DOMAIN")
    MAILGUN_FROM_EMAIL: str = os.getenv("MAILGUN_FROM_EMAIL", "no-reply@yourlostandfound.com")
    MAILGUN_FROM_NAME: str = os.getenv("MAILGUN_FROM_NAME", "YourLostAndFound.com")
    
    # Configuración de OTP
    OTP_EXPIRATION_MINUTES: int = 10 # Actualizado a 10 minutos como solicitaste

# Crear una instancia de la configuración para ser importada en otros archivos
settings = Settings()