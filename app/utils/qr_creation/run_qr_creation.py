# run_qr_creation.py

import argparse
import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

# --- Bloque de corrección de ruta sin cambios ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# --- Importaciones actualizadas ---
from app.db.database import SessionLocal
from app.utils.qr_creation.config import BASE_URL_ID, BRAND_OWNER_ID, QR_CODE_LENGTH, ACTIVATION_CODE_LENGTH
# CAMBIO: Se importan las nuevas funciones de generación
from app.utils.qr_creation.utils import generate_unique_short_id, generate_activation_code
from app.utils.qr_creation.image_handler import create_styled_qr_image

def process_qr_creation(db: Session):
    try:
        # --- Paso 1: Obtener la URL base (sin cambios) ---
        base_url_obj = db.execute(text("SELECT url FROM qr_base_url WHERE idqr_base_url = :id"), {"id": BASE_URL_ID}).fetchone()
        if not base_url_obj:
            raise Exception(f"No se encontró qr_base_url con id {BASE_URL_ID}")
        base_url = base_url_obj[0]

        # --- Novedad: Lógica de generación de códigos ANTES de la inserción ---
        # Paso 2: Generar los códigos únicos.
        unique_code = generate_unique_short_id(db, QR_CODE_LENGTH)
        activation_code = generate_activation_code(db, ACTIVATION_CODE_LENGTH)

        # Paso 3: Insertar el registro completo en 'identifiers' en un solo paso.
        # CAMBIO: Se usa la tabla 'identifiers' y se insertan 'code' y 'act_code'.
        sql_insert_qr = text("""
            INSERT INTO identifiers (qr_base_url_idqr_base_url, qr_brand_owner_id, status, origin_channel, code, act_code)
            VALUES (:base_id, :brand_id, 'GENERATED', 'manual', :code, :act_code)
        """)
        db.execute(sql_insert_qr, {
            "base_id": BASE_URL_ID, 
            "brand_id": BRAND_OWNER_ID, 
            "code": unique_code, 
            "act_code": activation_code
        })
        
        # Paso 4: Obtener el ID del nuevo registro.
        new_qr_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        
        # Paso 5: Generar la imagen QR, pasando ambos códigos.
        final_url = f"{base_url.rstrip('/')}/{unique_code}"
        # CAMBIO: Se pasa el `activation_code` a la función de imagen.
        image_path = create_styled_qr_image(final_url, unique_code, activation_code)
        if not image_path:
            raise Exception("La creación de la imagen falló.")

        # Paso 6: Registrar la ruta de la imagen en pic_route (sin cambios de lógica).
        sql_insert_pic = text("INSERT INTO pic_route (pic_route) VALUES (:path)")
        db.execute(sql_insert_pic, {"path": image_path})
        new_pic_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        
        # Paso 7: Actualizar 'identifiers' con el ID de la ruta de la imagen.
        # CAMBIO: Se actualiza la tabla 'identifiers'.
        sql_update_qr_with_pic_id = text("UPDATE identifiers SET pic_route_idpic_route = :pic_id WHERE idqr_codes = :id")
        db.execute(sql_update_qr_with_pic_id, {"pic_id": new_pic_id, "id": new_qr_id})

        # --- Final: Confirmar toda la transacción ---
        db.commit()

        print(f"Éxito! QR Creado:")
        print(f"  - ID en BD: {new_qr_id}")
        print(f"  - Código QR (ID): {unique_code}")
        # Novedad: Se muestra el código de activación.
        print(f"  - Código de Activación: {activation_code}")
        print(f"  - URL: {final_url}")
        print(f"  - Imagen guardada en: {image_path}")

    except Exception as e:
        print(f"ERROR: Ocurrió un problema. Revirtiendo cambios.")
        print(f"  - Detalle: {e}")
        db.rollback()

# La función main() no cambia y se mantiene igual.
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