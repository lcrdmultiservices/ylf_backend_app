# app/utils/qr_creation/config.py

# --- IDs estáticos para las inserciones en la base de datos.
BASE_URL_ID = 1
BRAND_OWNER_ID = 1

# --- Ruta absoluta para guardar las imágenes QR generadas.
STORAGE_PATH = "/var/www/html/ylf/backend_webapp/storage/qr_codes"

# --- Novedad: Longitudes de los códigos ---
QR_CODE_LENGTH = 7
ACTIVATION_CODE_LENGTH = 5

# --- Configuración de la imagen ---
TRANSPARENT_BACKGROUND = False

# Novedad: Se cambia al nuevo Estilo 3 para mostrar el código de activación.
BOTTOM_TEXT_STYLE = 3

TEXT_STYLES = {
    1: {
        "line1": "ID: {unique_code}",
        "line2": "yourlostandfound.com"
    },
    2: {
        "line1": "yourlostandfound.com/{unique_code}",
        "line2": ""
    },
    # Novedad: Estilo 3 que incluye el código de activación.
    3: {
        "line1": "ID: {unique_code}",
        "line2": "ACT: {activation_code}"
    }
}
# --- Configuración para la imagen ---
# DPI (puntos por pulgada) para la conversión de pulgadas a píxeles. 300 es estándar para impresión.
DPI = 300
# Tamaño del QR en pulgadas.
QR_SIZE_INCHES = 2
# Tamaño del QR en píxeles (calculado).
QR_SIZE_PIXELS = QR_SIZE_INCHES * DPI

# Espacio entre el texto y el borde superior del QR.
TEXT_PADDING_TOP = 8

# Fuente para el texto. Proporciona la ruta a un archivo .ttf o .otf.
# 'DejaVuSans.ttf' es una fuente común en sistemas Linux.
FONT_PATH = "DejaVuSans.ttf"
FONT_SIZE = 40 # Tamaño de la fuente en puntos.
