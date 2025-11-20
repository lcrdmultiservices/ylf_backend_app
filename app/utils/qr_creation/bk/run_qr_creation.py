import argparse
import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

# --- INICIO DE LA CORRECCIÓN DE RUTA ---
# Añade el directorio raíz del proyecto al path de Python.
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)
# --- FIN DE LA CORRECCIÓN DE RUTA ---


# Asegúrate de que estas importaciones coincidan con la estructura de tu proyecto.
from app.db.database import SessionLocal
from app.utils.qr_creation.config import BASE_URL_ID, BRAND_OWNER_ID
from app.utils.qr_creation.utils import generate_modular_code
from app.utils.qr_creation.image_handler import create_styled_qr_image

def process_qr_creation(db: Session):
    """
    Orquesta el proceso completo de creación de un código QR.
    """
    try:
        # --- Paso 1: Obtener la URL base ---
        base_url_obj = db.execute(text("SELECT url FROM qr_base_url WHERE idqr_base_url = :id"), {"id": BASE_URL_ID}).fetchone()
        if not base_url_obj:
            raise Exception(f"No se encontró qr_base_url con id {BASE_URL_ID}")
        base_url = base_url_obj[0]

        # --- CORRECCIÓN: Se omite product_instances_instance_id del INSERT inicial ---
        # Paso 2: Insertar registro inicial en qr_codes, dejando las FK opcionales como NULL.
        sql_insert_qr = text("""
            INSERT INTO qr_codes (qr_base_url_idqr_base_url, qr_brand_owner_id, status, origin_channel)
            VALUES (:base_id, :brand_id, 'GENERATED', 'manual')
        """)
        db.execute(sql_insert_qr, {"base_id": BASE_URL_ID, "brand_id": BRAND_OWNER_ID})
        
        # Paso 3: Obtener ID y Timestamp del nuevo registro de qr_codes ---
        new_qr_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        result = db.execute(text("SELECT created_at FROM qr_codes WHERE idqr_codes = :id"), {"id": new_qr_id}).fetchone()
        created_at_ts = result[0].timestamp()

        # Paso 4: Generar y actualizar el código único ---
        unique_code = generate_modular_code(new_qr_id, created_at_ts)
        db.execute(text("UPDATE qr_codes SET code = :code WHERE idqr_codes = :id"), {"code": unique_code, "id": new_qr_id})

        # Paso 5: Generar la imagen QR ---
        final_url = f"{base_url.rstrip('/')}/{unique_code}"
        image_path = create_styled_qr_image(final_url, unique_code)
        if not image_path:
            raise Exception("La creación de la imagen falló.")

        # Paso 6: Registrar la ruta de la imagen en pic_route.
        sql_insert_pic = text("INSERT INTO pic_route (pic_route) VALUES (:path)")
        db.execute(sql_insert_pic, {"path": image_path})
        new_pic_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        
        # Paso 7: Actualizar qr_codes con el ID de la ruta de la imagen.
        sql_update_qr_with_pic_id = text("UPDATE qr_codes SET pic_route_idpic_route = :pic_id WHERE idqr_codes = :id")
        db.execute(sql_update_qr_with_pic_id, {"pic_id": new_pic_id, "id": new_qr_id})
        # --- FIN DE LA CORRECCIÓN ---

        # --- Final: Confirmar toda la transacción ---
        db.commit()

        print(f"Éxito! QR Creado:")
        print(f"  - ID en BD: {new_qr_id}")
        print(f"  - Código: {unique_code}")
        print(f"  - URL: {final_url}")
        print(f"  - Imagen guardada en: {image_path}")

    except Exception as e:
        print(f"ERROR: Ocurrió un problema. Revirtiendo cambios.")
        print(f"  - Detalle: {e}")
        db.rollback()

def main():
    parser = argparse.ArgumentParser(description="Herramienta para la creación manual de códigos QR.")
    parser.add_argument("-n", "--number", type=int, default=1, help="Número de códigos QR a generar.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        for i in range(args.number):
            print(f"\n--- Procesando QR #{i+1} de {args.number} ---")
            process_qr_creation(db)
    finally:
        db.close()

if __name__ == "__main__":
    main()

