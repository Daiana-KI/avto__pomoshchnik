# app/services/local_tecdoc_service.py
import asyncpg
from typing import Dict, Any, Optional, List
from app.intelligent_search import find_relevant_parts

# Простой словарь для кэша: {car_id: [список_деталей]}
CACHE = {}

async def get_db_connection():
    # ⚠️ Здесь укажите параметры подключения к ВАШЕЙ локальной БД TecDoc
    conn = await asyncpg.connect(
        user='your_tecdoc_user',
        password='your_tecdoc_password',
        database='tecdoc_db',
        host='localhost'
    )
    return conn

async def search_in_local_db(vin: str, question: str) -> List[Dict]:
    print(f"📀 [Локальная БД] Поиск для VIN: {vin}, Вопрос: {question}")
    
    # --- 1. Находим car_id по VIN в локальной БД ---
    conn = await get_db_connection()
    # Замените 'cars' и 'vin' на реальные названия таблицы и поля в вашей БД TecDoc
    car_id = await conn.fetchval("SELECT car_id FROM cars WHERE vin = $1 LIMIT 1", vin)
    await conn.close()
    
    if not car_id:
        print(f"⚠️ [Локальная БД] Автомобиль с VIN {vin} не найден.")
        return []

    # --- 2. Проверяем, нет ли уже деталей для этого car_id в кэше ---
    if car_id in CACHE:
        print(f"✅ [Локальная БД] Данные для car_id {car_id} найдены в кэше.")
        all_parts = CACHE[car_id]
    else:
        # --- 3. Если в кэше нет, идем в БД и сохраняем результат ---
        print(f"🔄 [Локальная БД] car_id {car_id} не в кэше. Загружаем из БД...")
        conn = await get_db_connection()
        # Это пример. ВАМ НУЖНО НАПИСАТЬ СВОЙ SQL ЗАПРОС, ОСНОВЫВАЯСЬ НА СТРУКТУРЕ ВАШЕЙ БД.
        rows = await conn.fetch("""
            SELECT p.article_number AS article, p.article_name AS name, b.brand_name AS manufacturer
            FROM parts p
            JOIN car_parts cp ON p.part_id = cp.part_id
            JOIN brands b ON p.brand_id = b.brand_id
            WHERE cp.car_id = $1
        """, car_id)
        await conn.close()
        
        all_parts = [dict(row) for row in rows]
        CACHE[car_id] = all_parts  # Сохраняем в кэш
        print(f"✅ [Локальная БД] Загружено и закэшировано {len(all_parts)} деталей.")

    if not all_parts:
        return []

    # --- 4. Интеллектуальный поиск релевантных деталей ---
    relevant_parts = find_relevant_parts(question, all_parts, top_k=5)
    print(f"🎯 [Локальная БД] Найдено {len(relevant_parts)} релевантных деталей.")
    return relevant_parts