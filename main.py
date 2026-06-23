import logging
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from ocr_processor import extract_text_from_image
from product_matcher import find_products, get_eco_tip
from database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EcoScan API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok", "message": "EcoScan API работает"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "database": "подключена"}

@app.post("/api/analyze_receipt")
async def analyze_receipt(user_id: int = Form(...), image: UploadFile = File(...)):
    try:
        image_bytes = await image.read()
        if len(image_bytes) < 100:
            return {"status": "error", "message": "Изображение слишком маленькое или повреждено"}

        receipt_text = await extract_text_from_image(image_bytes)
        logger.info(f"Длина распознанного текста: {len(receipt_text)}")
        
        if not receipt_text or len(receipt_text) < 20:
            return {"status": "error", "message": "Не удалось распознать текст."}

        products = find_products(receipt_text)
        
        if len(products) == 0:
            return {"status": "error", "message": "Продукты из чека не найдены в базе данных."}

        total_co2 = sum(p['co2'] for p in products)  # ← словари!
        is_high = any(p['co2'] > 2.0 for p in products)  # ← словари!
        eco_tip = get_eco_tip(is_high)

        return {
            "status": "success",
            "data": {
                "products": products,  # ← уже словари, ничего не меняем
                "total_co2": total_co2,
                "is_high_emission": is_high,
                "eco_tip": eco_tip,
                "message": f"Найдено продуктов: {len(products)}"
            }
        }
    except Exception as e:
        logger.error(f"Ошибка анализа чека: {e}")
        return {"status": "error", "message": f"Ошибка при анализе чека: {str(e)}"}

@app.post("/api/reload_data")
async def reload_data():
    try:
        db.reload_data()
        return {"status": "success", "message": "Перезагрузка данных прошла успешно"}
    except Exception as e:
        return {"status": "error", "message": str(e)}