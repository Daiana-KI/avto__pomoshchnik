# app/parsers/parts_parser.py
from app.services.api_gateway import APIGateway

api_gateway = APIGateway()

# Временная заглушка для демонстрации (удалить после получения TecDoc API)
MOCK_PARTS = {
    "Z8NTANT32ES032071": {  # Nissan X-Trail 2019
        "диски": [
            {"name": "Тормозной диск передний", "article": "40206-4BA0A", "manufacturer": "Nissan"},
            {"name": "Тормозной диск задний", "article": "43206-4BA0A", "manufacturer": "Nissan"},
            {"name": "Диск тормозной вентилируемый", "article": "40206-4BA0B", "manufacturer": "Nissan"}
        ],
        "стойки": [
            {"name": "Стойка стабилизатора передняя", "article": "54618-4BA0A", "manufacturer": "Nissan"},
            {"name": "Стойка стабилизатора задняя", "article": "56261-4BA0A", "manufacturer": "Nissan"}
        ],
        "амортизаторы": [
            {"name": "Амортизатор передний", "article": "54302-4BA0A", "manufacturer": "Nissan"},
            {"name": "Амортизатор задний", "article": "56210-4BA0A", "manufacturer": "Nissan"}
        ],
        "ремни": [
            {"name": "Ремень ГРМ", "article": "11720-4BA0A", "manufacturer": "Nissan"},
            {"name": "Ремень приводной поликлиновой", "article": "11720-4BA0B", "manufacturer": "Nissan"}
        ],
        "сайлентблоки": [
            {"name": "Сайлентблок переднего рычага", "article": "54580-4BA0A", "manufacturer": "Nissan"}
        ],
        "подушки": [
            {"name": "Подушка двигателя передняя", "article": "11210-4BA0A", "manufacturer": "Nissan"}
        ],
        "термостат": [
            {"name": "Термостат", "article": "21200-4BA0A", "manufacturer": "Nissan"}
        ],
        "датчик": [
            {"name": "Датчик ABS", "article": "47900-4BA0A", "manufacturer": "Nissan"}
        ],
        "щётки": [
            {"name": "Щётки стеклоочистителя (комплект)", "article": "28890-4BA0A", "manufacturer": "Nissan"}
        ]
    }
}

async def search_parts_hybrid(vin: str, question: str, user_id: int):
    print(f"Начинаем для VIN: {vin}, Вопрос: '{question}'")

    # Проверяем временную заглушку
    mock_for_vin = MOCK_PARTS.get(vin)
    if mock_for_vin:
        question_lower = question.lower()
        for keyword, parts in mock_for_vin.items():
            if keyword in question_lower:
                print(f"🔧 Используем заглушку для VIN {vin} и ключевого слова '{keyword}'")
                return parts

    # Обычный вызов API (если заглушка не сработала)
    try:
        api_parts = await api_gateway.search_parts_by_vin(vin, question, user_id)
        if api_parts:
            return api_parts
    except Exception as e:
        print(f"Ошибка при вызове API: {e}")
    return []