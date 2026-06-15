from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.crud import get_all_car_models, get_car_model_by_id, add_user_car, delete_user_car
from app.schemas import CarModelOut, UserCarOut, UserCarCreate, ManualCarData, AddCarRequest
from app.models import CarModel, UserCar
from app.parsers.vin_parser import decode_vin
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/cars", tags=["cars"])
    
@router.get("/models", response_model=list[CarModelOut])
async def list_car_models(db: AsyncSession = Depends(get_db)):
    models = await get_all_car_models(db)
    return models

@router.get("/my", response_model=list[UserCarOut])
async def list_my_cars(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return []
    result = await db.execute(
        select(UserCar).where(UserCar.user_id == user_id).order_by(UserCar.created_at.desc())
    )
    user_cars = result.scalars().all()
    return user_cars

@router.get("/models/{car_model_id}", response_model=CarModelOut)
async def get_car_model(car_model_id: int, db: AsyncSession = Depends(get_db)):
    car_model = await get_car_model_by_id(db, car_model_id)
    if not car_model:
        raise HTTPException(status_code=404, detail="Модель не найдена")
    return car_model

@router.post("/my")
async def add_my_car(request: Request, data: AddCarRequest, db: AsyncSession = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Необходимо авторизоваться")
   
    if not data.vin or len(data.vin) != 17:
        raise HTTPException(status_code=400, detail="VIN обязателен и должен содержать 17 символов")
    
    # Пытаемся декодировать VIN через API
    car_info = await decode_vin(data.vin)
    
    car_model = None
    if car_info and car_info.get("brand"):
        # Успешное декодирование
        result = await db.execute(select(CarModel).where(CarModel.vin == data.vin))
        car_model = result.scalar_one_or_none()
        if not car_model:
            car_model = CarModel(
                vin=data.vin,
                brand=car_info["brand"],
                model=car_info["model"],
                year=car_info["year"],
                engine=car_info.get("engine"),
                transmission=car_info.get("transmission"),
                drive=car_info.get("drive")
            )
            db.add(car_model)
            await db.commit()
            await db.refresh(car_model)
    else:
        # Декодирование не удалось – используем ручные данные
        if not data.manual_data:
            raise HTTPException(status_code=400, detail="Не удалось декодировать VIN. Заполните данные вручную.")
        manual = data.manual_data
        result = await db.execute(select(CarModel).where(CarModel.vin == data.vin))
        car_model = result.scalar_one_or_none()
        if not car_model:
            car_model = CarModel(
                vin=data.vin,
                brand=manual.brand,
                model=manual.model,
                year=manual.year,
                engine=manual.engine,
                transmission=manual.transmission,
                drive=manual.drive
            )
            db.add(car_model)
            await db.commit()
            await db.refresh(car_model)
    
    if not car_model:
        raise HTTPException(status_code=500, detail="Не удалось создать модель автомобиля")
    
    # Проверяем, не добавлен ли уже этот автомобиль пользователю
    existing = await db.execute(
        select(UserCar).where(
            UserCar.user_id == user_id,
            UserCar.car_model_id == car_model.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Автомобиль уже добавлен")
    
    user_car = UserCar(user_id=user_id, car_model_id=car_model.id)
    db.add(user_car)
    await db.commit()
    await db.refresh(user_car)
    return {"id": user_car.id, "car_model_id": car_model.id}

@router.delete("/my/{user_car_id}")
async def delete_my_car(request: Request, user_car_id: int, db: AsyncSession = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Необходимо авторизоваться")
    result = await db.execute(
        select(UserCar).where(UserCar.id == user_car_id, UserCar.user_id == user_id)
    )
    user_car = result.scalar_one_or_none()
    if not user_car:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")
    await db.delete(user_car)
    await db.commit()
    return {"message": "Автомобиль удалён"}

@router.post("/decode_vin")
async def decode_vin_endpoint(vin_data: dict):
    vin = vin_data.get("vin", "").strip()
    if len(vin) != 17:
        raise HTTPException(status_code=400, detail="VIN должен быть 17 символов")
    car_info = await decode_vin(vin)
    if not car_info:
        raise HTTPException(status_code=404, detail="Не удалось декодировать VIN")
    return car_info 

@router.put("/my/{user_car_id}")
async def update_my_car(request: Request, user_car_id: int, data: ManualCarData, db: AsyncSession = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Необходимо авторизоваться")
    
    result = await db.execute(
        select(UserCar).where(UserCar.id == user_car_id, UserCar.user_id == user_id)
    )
    user_car = result.scalar_one_or_none()
    if not user_car:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")
    
    result = await db.execute(select(CarModel).where(CarModel.id == user_car.car_model_id))
    car_model = result.scalar_one_or_none()
    if car_model:
        car_model.brand = data.brand
        car_model.model = data.model
        car_model.year = data.year
        car_model.engine = data.engine
        car_model.transmission = data.transmission
        car_model.drive = data.drive
        await db.commit()
    
    return {"message": "Автомобиль обновлён"}