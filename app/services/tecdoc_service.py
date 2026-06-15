# app/services/tecdoc_api.py
import httpx

TECDOC_API_KEY = "01186691560aa5dbda9f7be1c2dcc7ec"  # тестовый ключ TecDoc
BASE_URL = "https://api.tecdoc.net/v1"  # официальный URL TecDoc API

async def get_parts_by_vin(vin: str, cat: str):
    params = {
        "method": "getPartsbyVIN",
        "key": TECDOC_API_KEY,
        "vin": vin,
        "type": "oem",
        "cat": cat,
        "lang": "ru"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        # Парсинг ответа TecDoc (пример)
        parts = []
        for item in data.get("data", []):
            parts_str = item.get("parts", "")
            if parts_str:
                brand, article = parts_str.split("|")
                parts.append({
                    "name": item.get("shortname", ""),
                    "article": article,
                    "manufacturer": brand
                })
        return parts