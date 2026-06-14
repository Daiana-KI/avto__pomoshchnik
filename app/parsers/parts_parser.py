# app/parsers/hybrid_parts_parser.py
from app.services.api_gateway import APIGateway
from app.services.tecdoc_service import search_in_local_db

api_gateway = APIGateway()

async def search_parts_hybrid(vin: str, question: str):
    print(f"🚀 [Гибридный поиск] Начинаем для VIN: {vin}, Вопрос: '{question}'")

    # 1. Пытаемся через API
    api_parts = await api_gateway.search_parts_by_vin(vin, question)
    if api_parts:
        print(f"✅ Данные получены из API.")
        return api_parts

    # 2. Если API не ответил (заглушка вернула None) – идём в локальную БД
    print(f"🔄 API не ответил. Переключаемся на локальную БД.")
    local_parts = await search_in_local_db(vin, question)
    if local_parts:
        print(f"✅ Данные получены из локальной БД.")
        return local_parts

    print(f"❌ Данные не найдены ни в API, ни в локальной БД.")
    return []