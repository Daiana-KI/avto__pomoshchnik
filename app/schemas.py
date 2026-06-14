from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str]

class Token(BaseModel):
    access_token: str
    token_type: str

# Глобальные модели
class CarModelCreate(BaseModel):
    vin: str   
    brand: str
    model: str
    year: int
    engine: Optional[str] = None
    transmission: Optional[str] = None
    drive: Optional[str] = None

class CarModelOut(CarModelCreate):
    id: int

class ManualCarData(BaseModel):
    vin: str
    brand: str
    model: str
    year: int
    engine: Optional[str] = None
    transmission: Optional[str] = None
    drive: Optional[str] = None

class AddCarRequest(BaseModel):
    vin: str   
    manual_data: Optional[ManualCarData] = None

# Связь пользователя с автомобилем (упрощённая)
class UserCarCreate(BaseModel):
    car_model_id: int

class UserCarOut(BaseModel):
    id: int
    user_id: int
    car_model_id: int
    created_at: datetime