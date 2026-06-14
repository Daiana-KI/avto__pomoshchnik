# app/routers/ask.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud import get_car_model_by_id
from app.parsers.parts_parser import search_parts_hybrid as search_parts_all_sources
from pydantic import BaseModel
from app.parsers.parts_parser import search_parts_hybrid as search_parts_all_sources
from app.intelligent_search import find_relevant_parts

router = APIRouter(prefix="/ask", tags=["ask"])

class QuestionRequest(BaseModel):
    car_model_id: int
    question: str

@router.post("/")
async def ask(request: Request, question_data: QuestionRequest, db: AsyncSession = Depends(get_db)):
    car_model = await get_car_model_by_id(db, question_data.car_model_id)
    if not car_model:
        raise HTTPException(status_code=404, detail="Модель автомобиля не найдена")
    
    question = question_data.question
    vin = car_model.vin  # должно быть поле vin в car_models!

    # Ищем запчасти интеллектуально (по смыслу)
    parts = await search_parts_all_sources(vin=vin, question=question)

    if parts:
        answer = f"Релевантные запчасти для {car_model.brand} {car_model.model}:\n\n"
        for p in parts[:8]:
            price_str = f"{p['price']} ₽" if p.get('price') else "цена не указана"
            sim = p.get('similarity', 0)
            answer += f"• {p['name']} (арт. {p['article']}) — {price_str} (совпадение: {sim:.0%})\n"
        return {"answer": answer}
    
    # Если не нашли — возможно, вопрос о поломке (короткий список ключевых слов, но это не rule‑based, а просто утилита)
    breakdown_keywords = ['заглох', 'не заводится', 'стук', 'перегрев', 'дымит', 'чек']
    if any(kw in question.lower() for kw in breakdown_keywords):
        answer = f"Инструкция для {car_model.brand} {car_model.model}:\n\n1. Проверьте уровень топлива\n2. Проверьте аккумулятор\n3. Обратитесь на СТО"
    else:
        answer = f"Запчасти по вашему запросу не найдены. Попробуйте переформулировать вопрос."
    
    return {"answer": answer}

