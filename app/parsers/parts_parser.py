from app.services.tecdoc_gateway import TecDocGateway
from app.intelligent_search import find_relevant_parts

API_KEY = "hgHFioLn6kZHewCI2kGdRqja8Fr3cOaN0Z4iMNZXEQWtqn0LESk4Is6pbQEG"
gateway = TecDocGateway(API_KEY)

MAX_PARTS_FOR_RANKING = 20

async def search_parts_hybrid(vin: str, question: str, original_question: str, user_id: int):
    print(f"Начинаем для VIN: {vin}, Вопрос: '{question}'")
    print(f"Оригинальный вопрос (без контекста): '{original_question}'")
    try:
        car_info = await gateway.get_vin_info(vin)
        if not car_info:
            print("Не удалось получить gen_id")
            return []
        gen_id = car_info["gen_id"]

        # 1. Получаем все категории с оценками сходства (по оригинальному вопросу)
        cat_results = await gateway.find_categories_with_scores(gen_id, original_question)
        if not cat_results:
            print("Не найдено подходящих категорий")
            return []

        # 2. Фильтруем категории по ключевым словам из оригинального вопроса
        question_lower = original_question.lower()
        keywords = [w for w in question_lower.split() if len(w) > 3]
        if keywords:
            filtered_cats = []
            for cat in cat_results:
                cat_name = cat['name'].lower()
                if any(kw in cat_name for kw in keywords):
                    filtered_cats.append(cat)
            if filtered_cats:
                cat_results = filtered_cats
                print(f"Отфильтровано категорий по ключевым словам: {len(cat_results)}")
            else:
                print("Нет категорий, содержащих ключевые слова, используем все категории")
                return []

        selected_cats = cat_results[:1]
        print(f"Выбрано категорий для поиска: {len(selected_cats)}")
        for cat in selected_cats:
            print(f"  - {cat['name']} (score: {cat['score']:.4f})")

        # 4. Собираем детали из выбранных категорий
        all_parts = []
        used_str_id = None
        for cat in selected_cats:
            used_str_id = cat["str_id"]
            parts_data = await gateway.get_parts(gen_id, cat["str_id"])
            limited_parts = parts_data[:MAX_PARTS_FOR_RANKING]
            print(f"Категория '{cat['name']}': получено {len(parts_data)} деталей, ограничено до {len(limited_parts)}")
            for item in limited_parts:
                all_parts.append({
                    "name": item.get("ART_PRODUCT_NAME") or item.get("PRODUCT_GROUP") or "",
                    "article": item.get("ART_ARTICLE_NR") or "",
                    "manufacturer": item.get("SUP_BRAND") or "",
                    "price": item.get("price") or None,
                    "COUNTRY": item.get("COUNTRY") or "",
                    "ARTICLE_CRITERIA": item.get("ARTICLE_CRITERIA", []),
                    "source": "TecDoc API",
                    "category_name": cat["name"],
                    "score": cat["score"]
                })

        if all_parts:
            print(f"Всего собрано {len(all_parts)} запчастей")
            # 5. Ранжируем детали по смыслу (с учётом контекста — question)
            relevant = await find_relevant_parts(
                question,   # вопрос с контекстом
                all_parts,
                gen_id,
                used_str_id,
                top_k=8,
                threshold=0.3
            )
            if relevant:
                print(f"Отобрано {len(relevant)} релевантных запчастей")
                return relevant
            else:
                # Если ничего не прошло порог, возвращаем первые 8
                return all_parts[:8]
        return []

    except Exception as e:
        print(f"Ошибка TecDoc API: {e}")
        return []