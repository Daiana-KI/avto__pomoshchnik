# app/services/api_gateway.py
import httpx
from typing import Dict, Any, Optional, List

# ⚠️ ВРЕМЕННЫЙ ПЛЕЙСХОЛДЕР. СЮДА ВСТАВИТЕ ВАШ НАСТОЯЩИЙ КЛЮЧ.
PLACEHOLDER_API_KEY = "ВАШ_BУДУЩИЙ_API_КЛЮЧ"

class APIGateway:
    def __init__(self):
        self.base_url = "https://api.partsapi.ru" # Или URL вашего будущего API

    async def search_parts_by_vin(self, vin: str, question: str) -> Optional[List[Dict]]:
        """
        Ищет запчасти через внешний API.
        Сейчас - демо-режим (всегда возвращает None, имитируя отсутствие ключа).
        При получении реального ключа - раскомментируйте реальный код.
        """
        print(f"🟡 [API Gateway] Запрос к API (режим ожидания ключа). VIN: {vin}, Вопрос: {question}")
        
        # ⚠️ ВРЕМЕННАЯ ЗАГЛУШКА. ПОКА API НЕ НАСТРОЕН, ВСЕГДА ВОЗВРАЩАЕМ None.
        # Это заставит приложение переключиться на локальную БД.
        return None

        # --- РЕАЛЬНЫЙ КОД (РАСКОММЕНТИРУЕТЕ, КОГДА ПОЛУЧИТЕ КЛЮЧ) ---
        # if not PLACEHOLDER_API_KEY or PLACEHOLDER_API_KEY == "ВАШ_BУДУЩИЙ_API_КЛЮЧ":
        #     print("🔴 [API Gateway] API ключ не настроен.")
        #     return None
        #
        # params = {
        #     "method": "getPartsbyVIN",
        #     "key": PLACEHOLDER_API_KEY,
        #     "vin": vin,
        #     "type": "oem",
        #     "cat": "1191",  # Категорию можно будет определять по вопросу
        # }
        # 
        # async with httpx.AsyncClient(timeout=30) as client:
        #     try:
        #         response = await client.get(self.base_url, params=params)
        #         response.raise_for_status()
        #         data = response.json()
        #         # ... здесь парсинг ответа API в единый формат ...
        #         print(f"✅ [API Gateway] Успешный ответ от API")
        #         return parsed_parts
        #     except Exception as e:
        #         print(f"❌ [API Gateway] Ошибка при вызове API: {e}")
        #         return None