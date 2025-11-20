import time

BASE62_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
# El número máximo que se puede representar con 6 caracteres en Base62 (62^6)
MAX_VAL_6_CHARS = 56800235583

def to_base62(num: int) -> str:
    """Codifica un número entero a una cadena en Base62."""
    if num == 0:
        return BASE62_CHARS[0]
    
    encoded = ""
    base = len(BASE62_CHARS)
    
    while num > 0:
        num, rem = divmod(num, base)
        encoded = BASE62_CHARS[rem] + encoded
        
    return encoded

def generate_modular_code(record_id: int, timestamp: float) -> str:
    """
    Genera un código corto, único y no predecible basado en el ID y timestamp de un registro.
    """
    # 1. Usar el timestamp del registro (convertido a nanosegundos para más entropía)
    timestamp_ns = int(timestamp * 1_000_000_000)

    # 2. Combinar el ID y el tiempo usando números primos para "mezclar"
    base_number = (timestamp_ns * 31) + (record_id * 53)

    # 3. Usar el módulo para asegurar que el número cabe en 6 caracteres Base62
    final_number = base_number % MAX_VAL_6_CHARS
    
    # 4. Codificar el número final a Base62
    short_code = to_base62(final_number)
    
    # 5. Asegurar que tenga al menos 4 caracteres, añadiendo ceros a la izquierda si es necesario
    return short_code.zfill(4)
