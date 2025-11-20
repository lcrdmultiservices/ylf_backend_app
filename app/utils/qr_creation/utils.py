import secrets
import string
from sqlalchemy.orm import Session
from sqlalchemy import text

# --- Novedad: Separamos los alfabetos para cada tipo de código ---

# Alfabeto completo (62 caracteres) para el identificador del QR, que no necesita ser escrito por humanos.
QR_CODE_ALPHABET = string.ascii_letters + string.digits

# Alfabeto legible para humanos (32 caracteres) para el código de activación.
# Se eliminan caracteres ambiguos como O, 0, I, 1, l.
ACTIVATION_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_unique_short_id(db: Session, length: int) -> str:
    """
    Genera un identificador corto, aleatorio y único para el código QR.
    Verifica contra la base de datos para garantizar que no haya colisiones.
    """
    while True:
        # 1. Generar una cadena aleatoria usando un método criptográficamente seguro.
        short_id = ''.join(secrets.choice(QR_CODE_ALPHABET) for _ in range(length))
        
        # 2. Verificar que el código no exista en la tabla 'identifiers'.
        query = text("SELECT 1 FROM identifiers WHERE code = :code_to_check")
        exists = db.execute(query, {"code_to_check": short_id}).first()
        
        if not exists:
            return short_id


def generate_activation_code(db: Session, length: int) -> str:
    """
    Genera un código de activación corto, aleatorio, legible y único.
    Verifica contra la base de datos para garantizar que no haya colisiones.
    """
    while True:
        # 1. Generar una cadena aleatoria usando el alfabeto legible.
        act_code = ''.join(secrets.choice(ACTIVATION_CODE_ALPHABET) for _ in range(length))
        
        # 2. Verificar que el código no exista en la tabla 'identifiers'.
        query = text("SELECT 1 FROM identifiers WHERE act_code = :code_to_check")
        exists = db.execute(query, {"code_to_check": act_code}).first()
        
        if not exists:
            return act_code