# --- CONFIGURACIÓN CENTRALIZADA PARA LA GENERACIÓN DE QR ---

# IDs estáticos para las inserciones en la base de datos.
BASE_URL_ID = 1
BRAND_OWNER_ID = 1

# Ruta absoluta para guardar las imágenes QR generadas.
# Asegúrate de que esta carpeta exista y tenga permisos de escritura.
STORAGE_PATH = "/var/www/html/ylf/backend_webapp/storage/qr_codes"

TRANSPARENT_BACKGROUND = False

BOTTOM_TEXT_STYLE = 2

TEXT_STYLES = {
    1: {
        "line1": "ID: {}",
        "line2": "yourlostandfound.com"
    },
    2: {
        "line1": "yourlostandfound.com/{}",
        "line2": ""  # Dejar vacío para no tener segunda línea
    }
    # Puedes añadir más estilos aquí en el futuro (ej: Estilo 3)
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
