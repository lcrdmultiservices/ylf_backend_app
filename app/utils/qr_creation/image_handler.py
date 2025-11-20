# app/utils/qr_creation/image_handler.py

from PIL import Image, ImageDraw, ImageFont
import qrcode
import os
from .config import STORAGE_PATH, TRANSPARENT_BACKGROUND, BOTTOM_TEXT_STYLE, TEXT_STYLES

# La función find_optimal_font_size no cambia y se mantiene igual.
def find_optimal_font_size(text, font_path, desired_width):
    if not text:
        return None
    font_size = 1
    font = ImageFont.truetype(font_path, font_size)
    while font.getlength(text) < desired_width:
        font_size += 1
        font = ImageFont.truetype(font_path, font_size)
    font_size -= 1
    return ImageFont.truetype(font_path, max(1, font_size))

# CAMBIO: La función ahora acepta `activation_code` como parámetro.
def create_styled_qr_image(data_url: str, unique_code: str, activation_code: str) -> str | None:
    try:
        qr_size_in_inches = 2
        dpi = 300
        qr_pixel_size = qr_size_in_inches * dpi
        padding = int(dpi * 0.1)
        texto_superior = "Scan if found"

        font_path = os.path.join(os.path.dirname(__file__), "Inter-Regular.ttf")
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"No se encontró la fuente en {font_path}.")

        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=30, border=2)
        qr.add_data(data_url)
        qr.make(fit=True)
        qr_back_color = "transparent" if TRANSPARENT_BACKGROUND else "white"
        qr_img = qr.make_image(fill_color="black", back_color=qr_back_color)
        qr_img = qr_img.resize((qr_pixel_size, qr_pixel_size), Image.Resampling.LANCZOS)

        target_text_width = qr_pixel_size * 0.95
        font_superior = find_optimal_font_size(texto_superior, font_path, target_text_width)
        
        style_config = TEXT_STYLES.get(BOTTOM_TEXT_STYLE, TEXT_STYLES[1])
        
        # CAMBIO: Se pasan ambos códigos al método format.
        texto_inferior_1 = style_config.get("line1", "").format(unique_code=unique_code, activation_code=activation_code)
        texto_inferior_2 = style_config.get("line2", "").format(unique_code=unique_code, activation_code=activation_code)
        
        font_inferior_1 = find_optimal_font_size(texto_inferior_1, font_path, target_text_width)
        font_inferior_2 = find_optimal_font_size(texto_inferior_2, font_path, target_text_width)
        
        alto_texto_superior = font_superior.getbbox(texto_superior)[3] if font_superior else 0
        alto_texto_inferior_1 = font_inferior_1.getbbox(texto_inferior_1)[3] if font_inferior_1 else 0
        alto_texto_inferior_2 = font_inferior_2.getbbox(texto_inferior_2)[3] if font_inferior_2 else 0
        
        altura_total = alto_texto_superior + qr_pixel_size + padding * 2
        if alto_texto_inferior_1 > 0:
            altura_total += alto_texto_inferior_1 + 10
        if alto_texto_inferior_2 > 0:
            altura_total += alto_texto_inferior_2 + padding // 2

        ancho_total = qr_pixel_size

        if TRANSPARENT_BACKGROUND:
            lienzo = Image.new('RGBA', (ancho_total, int(altura_total)), (255, 255, 255, 0))
            qr_img = qr_img.convert('RGBA')
        else:
            lienzo = Image.new('RGB', (ancho_total, int(altura_total)), 'white')
            qr_img = qr_img.convert('RGB')
        
        draw = ImageDraw.Draw(lienzo)

        pos_y_actual = padding
        if font_superior:
            ancho_texto_sup = draw.textlength(texto_superior, font=font_superior)
            pos_x_sup = (ancho_total - ancho_texto_sup) / 2
            draw.text((pos_x_sup, pos_y_actual), texto_superior, font=font_superior, fill="black")
            pos_y_actual += alto_texto_superior + padding
        
        pos_y_qr = pos_y_actual
        if TRANSPARENT_BACKGROUND:
            lienzo.paste(qr_img, (0, int(pos_y_qr)), mask=qr_img)
        else:
            lienzo.paste(qr_img, (0, int(pos_y_qr)))
        pos_y_actual += qr_pixel_size

        if font_inferior_1:
            pos_y_actual += 10
            ancho_texto_inf1 = draw.textlength(texto_inferior_1, font=font_inferior_1)
            pos_x_inf1 = (ancho_total - ancho_texto_inf1) / 2
            draw.text((pos_x_inf1, pos_y_actual), texto_inferior_1, font=font_inferior_1, fill="black")
            pos_y_actual += alto_texto_inferior_1

        if font_inferior_2:
            pos_y_actual += padding // 2
            ancho_texto_inf2 = draw.textlength(texto_inferior_2, font=font_inferior_2)
            pos_x_inf2 = (ancho_total - ancho_texto_inf2) / 2
            draw.text((pos_x_inf2, pos_y_actual), texto_inferior_2, font=font_inferior_2, fill="black")

        os.makedirs(STORAGE_PATH, exist_ok=True)
        image_path = os.path.join(STORAGE_PATH, f"{unique_code}.png")
        lienzo.save(image_path, dpi=(dpi, dpi))
        
        return image_path

    except Exception as e:
        print(f"Error al generar la imagen del QR: {e}")
        return None