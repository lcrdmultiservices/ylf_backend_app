# create_provisional_qr.py
import argparse
from qr_manager import create_qr_record
from image_generator import generate_qr_image

def main():
    parser = argparse.ArgumentParser(description="Crea un registro de QR en la BD y genera su imagen.")
    parser.add_argument("--url", required=True, help="La URL de destino a la que apuntará el QR.")
    parser.add_argument("--texto-sup", default="¿Me encontraste?", help="Texto superior de la imagen.")
    parser.add_argument("--texto-inf", default="Escanéame", help="Texto inferior de la imagen.")
    
    args = parser.parse_args()
    
    print("Iniciando proceso de creación de QR...")
    
    # 1. Crear el registro en la base de datos usando el manager
    qr_data = create_qr_record(args.url)
    
    if not qr_data:
        print("Fallo al crear el registro en la base de datos. Abortando.")
        return

    # 2. Generar la imagen usando el generador
    print(f"Generando imagen para la URL: {qr_data['qr_url']}...")
    
    # Puedes personalizar el texto inferior para que incluya el código, por ejemplo
    texto_inferior_personalizado = f"{args.texto_inf} ({qr_data['code']})"
    
    success = generate_qr_image(
        data_url=qr_data['qr_url'],
        texto_superior=args.texto_sup,
        texto_inferior=texto_inferior_personalizado,
        output_path=qr_data['image_path']
    )
    
    if success:
        print("-" * 30)
        print("¡Proceso completado con éxito! ✅")
        print(f"Código Único: {qr_data['code']}")
        print(f"URL del QR: {qr_data['qr_url']}")
        print(f"Imagen guardada en: {qr_data['image_path']}")
        print("-" * 30)
    else:
        print("Fallo al generar el archivo de imagen.")

if __name__ == "__main__":
    main()