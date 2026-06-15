from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User, CarModel, UserCar
from app.cache import cached

@cached(expire=86400)  # кэш на сутки
async def get_car_model_by_id(db: AsyncSession, car_model_id: int):
    result = await db.execute(select(CarModel).where(CarModel.id == car_model_id))
    return result.scalar_one_or_none()

@cached(expire=86400)
async def get_all_car_models(db: AsyncSession):
    result = await db.execute(select(CarModel))
    return result.scalars().all()

# ---------- Пользователи ----------
async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str):
    if email:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    return None

async def create_user(db: AsyncSession, username: str, email: str, password: str):
    from app.auth import get_password_hash
    hashed = get_password_hash(password)
    db_user = User(username=username, email=email, hashed_password=hashed)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

# ---------- Глобальные модели автомобилей (админ) ----------
async def get_all_car_models(db: AsyncSession):
    result = await db.execute(select(CarModel))
    return result.scalars().all()

async def get_car_model_by_id(db: AsyncSession, car_model_id: int):
    result = await db.execute(select(CarModel).where(CarModel.id == car_model_id))
    return result.scalar_one_or_none()

# ---------- Автомобили пользователя ----------
async def get_user_cars(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(UserCar).where(UserCar.user_id == user_id).order_by(UserCar.created_at.desc())
    )
    return result.scalars().all()

async def add_user_car(db: AsyncSession, user_id: int, car_model_id: int):
    existing = await db.execute(
        select(UserCar).where(UserCar.user_id == user_id, UserCar.car_model_id == car_model_id)
    )
    if existing.scalar_one_or_none():
        return None
    user_car = UserCar(user_id=user_id, car_model_id=car_model_id)
    db.add(user_car)
    await db.commit()
    await db.refresh(user_car)
    return user_car

async def delete_user_car(db: AsyncSession, user_car_id: int, user_id: int):
    result = await db.execute(
        select(UserCar).where(UserCar.id == user_car_id, UserCar.user_id == user_id)
    )
    user_car = result.scalar_one_or_none()
    if user_car:
        await db.delete(user_car)
        await db.commit()
    return user_car

