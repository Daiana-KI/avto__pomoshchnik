# app/routers/ask.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud import get_car_model_by_id
from app.parsers.parts_parser import search_parts_hybrid as search_parts_all_sources
from pydantic import BaseModel
import os

router = APIRouter(prefix="/ask", tags=["ask"])

class QuestionRequest(BaseModel):
    car_model_id: int
    question: str

# Временное хранилище контекста (in-memory)
context_store = {}

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

    # ----- Контекст диалога (in-memory) -----
    full_question = question
    MAX_HISTORY = int(os.getenv("DIALOG_MAX_HISTORY", "5"))
    user_key = str(user_id)
    
    # Загружаем историю
    last_messages = context_store.get(user_key, [])[-MAX_HISTORY:]
    context_text = ""
    for msg in last_messages:
        context_text += msg + "\n"
    if context_text:
        full_question = f"{context_text}Пользователь: {question}"
        print(f"Контекст добавлен: {full_question[:100]}...")
    else:
        print("Контекст пуст, используем исходный вопрос")

    # Ищем запчасти (передаём вопрос с контекстом)
    parts = await search_parts_all_sources(vin=vin, question=full_question, user_id=user_id)

    if parts:
        answer = f"Релевантные запчасти для {car_model.brand} {car_model.model}:\n\n"
        for p in parts[:8]:
            price_str = f"{p['price']} ₽" if p.get('price') else "цена не указана"
            sim = p.get('similarity', 0)
            answer += f"• {p['name']} (арт. {p['article']}) — {price_str} (совпадение: {sim:.0%})\n"
    else:
        breakdown_keywords = ['заглох', 'не заводится', 'стук', 'перегрев', 'дымит', 'чек']
        if any(kw in question.lower() for kw in breakdown_keywords):
            answer = f"Инструкция для {car_model.brand} {car_model.model}:\n\n1. Проверьте уровень топлива\n2. Проверьте аккумулятор\n3. Обратитесь на СТО"
        else:
            answer = "Запчасти по вашему запросу не найдены. Попробуйте переформулировать вопрос."

    # Сохраняем диалог в словарь
    history_entry = f"Вопрос: {question}\nОтвет: {answer}"
    hist = context_store.get(user_key, [])
    hist.append(history_entry)
    context_store[user_key] = hist[-MAX_HISTORY:]

    return {"answer": answer}