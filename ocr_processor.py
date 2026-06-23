import cv2
import numpy as np
from PIL import Image, ImageEnhance
import pytesseract
from openai import OpenAI
from config import config
import os
import subprocess

# Настройка tesseract
try:
    subprocess.run(['tesseract', '--version'], capture_output=True, check=True)
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'
except:
    possible_paths = ['/usr/bin/tesseract', '/usr/local/bin/tesseract']
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break

client = OpenAI(api_key=config.openai_key) if config.openai_key else None

def preprocess_image(image_bytes):
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        height, width = img.shape[:2]
        if width < 1500:
            scale = 2000 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        denoised = cv2.fastNlMeansDenoising(enhanced, h=30)
        binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

        pil_img = Image.fromarray(binary)
        sharpen = ImageEnhance.Sharpness(pil_img)
        return sharpen.enhance(1.5)
    except:
        return None

async def correct_ocr_with_gpt(ocr_text):
    if not client:
        return ocr_text
    try:
        prompt = f"""Ты эксперт по исправлению OCR-ошибок в чеках. ВАЖНЫЕ ПРАВИЛА:
1. Текст чеков на РУССКОМ языке. Не переводи ничего на английский или другие языки.
2. ТОРГОВЫЕ НАИМЕНОВАНИЯ (бренды, названия продуктов) НЕЛЬЗЯ заменять или переводить.
3. Исправляй только явные опечатки (буквы, цифры).
4. НЕ удаляй пробелы и дефисы в названиях.
5. Сохраняй оригинальную структуру строк.
6. Не переводи и не переименовывай продукты.
7. Сохраняй КАЖДУЮ строку чека.
8. НЕ УДАЛЯЙ и НЕ ОБЪЕДИНЯЙ строки с продуктами.

Оригинальный OCR-текст:
{ocr_text}

Верни ТОЛЬКО исправленный текст, сохраняя все строки, без пояснений и комментариев."""
        response = client.chat.completions.create(model="gpt-4.1-mini", messages=[{"role": "user", "content": prompt}], max_tokens=2000, temperature=0.1)
        return response.choices[0].message.content
    except:
        return ocr_text

async def extract_text_from_image(image_bytes):
    try:
        processed = preprocess_image(image_bytes)
        if processed is None:
            return ""
        text1 = pytesseract.image_to_string(processed, lang='rus+eng', config='--oem 3 --psm 6')
        text2 = pytesseract.image_to_string(processed, lang='rus+eng', config='--oem 3 --psm 3')
        text3 = pytesseract.image_to_string(processed, lang='rus+eng', config='--oem 3 --psm 11')
        combined = text1 + "\n" + text2 + "\n" + text3
        combined = await correct_ocr_with_gpt(combined)
        return combined.lower()
    except:
        return ""