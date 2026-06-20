# app/routers/ask.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud import get_car_model_by_id
from app.parsers.parts_parser import search_parts_hybrid as search_parts_all_sources
from app.services.tecdoc_gateway import TecDocGateway
from pydantic import BaseModel
import os

router = APIRouter(prefix="/ask", tags=["ask"])

class QuestionRequest(BaseModel):
    car_model_id: int
    question: str

context_store = {}

API_KEY = "hgHFioLn6kZHewCI2kGdRqja8Fr3cOaN0Z4iMNZXEQWtqn0LESk4Is6pbQEG"
gateway = TecDocGateway(API_KEY)

@router.post("/")
async def ask(request: Request, question_data: QuestionRequest, db: AsyncSession = Depends(get_db)):
    car_model = await get_car_model_by_id(db, question_data.car_model_id)
    if not car_model:
        raise HTTPException(status_code=404, detail="Модель автомобиля не найдена")
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Необходимо авторизоваться")
    
    question = question_data.question
    vin = car_model.vin

    full_question = question
    MAX_HISTORY = int(os.getenv("DIALOG_MAX_HISTORY", "5"))
    user_key = str(user_id)
    
    last_messages = context_store.get(user_key, [])[-MAX_HISTORY:]
    context_text = ""
    for msg in last_messages:
        context_text += msg + "\n"
    if context_text:
        full_question = f"{context_text}Пользователь: {question}"
        print(f"Контекст добавлен: {full_question[:100]}...")
    else:
        print("Контекст пуст, используем исходный вопрос")

    parts = await search_parts_all_sources(vin=vin, question=full_question, original_question=question, user_id=user_id)

    if parts:
        side_keyword = None
        question_lower = question.lower()
        if "передн" in question_lower:
            side_keyword = "передн"
        elif "задн" in question_lower:
            side_keyword = "задн"
        elif "лев" in question_lower:
            side_keyword = "лев"
        elif "прав" in question_lower:
            side_keyword = "прав"

        if side_keyword:
            parts = gateway.filter_parts_by_side(parts, side_keyword)

        answer = f"🔧 Релевантные запчасти для {car_model.brand} {car_model.model}:\n\n"
        for idx, p in enumerate(parts[:8], 1):
            name = p.get('name') or p.get('ART_PRODUCT_NAME') or p.get('PRODUCT_GROUP') or "Без названия"
            article = p.get('article') or p.get('ART_ARTICLE_NR') or ""
            brand = p.get('manufacturer') or p.get('SUP_BRAND') or ""
            country = p.get('COUNTRY') or ""

            price = p.get('price') or p.get('PRICE') or None
            price_str = f"{price} ₽" if price else "цена не указана"

            criteria = p.get('ARTICLE_CRITERIA', [])
            details = []
            for crit in criteria:
                cri_name = crit.get('CRI_NAME', '')
                cri_des = crit.get('CRI_DES') or crit.get('CRI_VALUE', '')
                if cri_name and cri_des:
                    details.append(f"{cri_name}: {cri_des}")
                elif cri_des:
                    details.append(cri_des)
            unique_details = []
            for d in details:
                if d not in unique_details:
                    unique_details.append(d)
            details_str = "\n   ".join(unique_details) if unique_details else ""

            answer += f"{idx}. **{name}**\n"
            answer += f"   📦 Артикул: {article}\n"
            if brand:
                answer += f"   🏷️ Бренд: {brand}\n"
            if country:
                answer += f"   🌍 Страна: {country}\n"
            answer += f"   💰 Цена: {price_str}\n"
            if details_str:
                answer += f"   📋 Характеристики:\n   {details_str}\n"
            answer += "\n"
    else:
        car_info = await gateway.get_vin_info(vin)
        if car_info and car_info.get("gen_id"):
            gen_id = car_info["gen_id"]
            cat_results = await gateway.find_categories_with_scores(gen_id, full_question)
            top_cats = [c for c in cat_results if c["score"] >= 0.3]
            if len(top_cats) >= 2:
                options = []
                for idx, cat in enumerate(top_cats[:3], 1):
                    options.append(f"{idx}. {cat['name']}")
                answer = f"🤔 Уточните, что вы имеете в виду:\n" + "\n".join(options) + "\n\n(Напишите номер или название)"
            else:
                answer = "❌ Запчасти по вашему запросу не найдены. Попробуйте переформулировать вопрос."
        else:
            answer = "❌ Запчасти по вашему запросу не найдены. Попробуйте переформулировать вопрос."

    history_entry = f"Вопрос: {question}\nОтвет: {answer}"
    hist = context_store.get(user_key, [])
    hist.append(history_entry)
    context_store[user_key] = hist[-MAX_HISTORY:]

    return {"answer": answer}