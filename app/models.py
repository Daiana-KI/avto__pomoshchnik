from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    reset_token = Column(String, nullable=True)           
    reset_token_expiry = Column(DateTime, nullable=True)

    user_cars = relationship("UserCar", back_populates="user", cascade="all, delete-orphan")

class CarModel(Base):
    __tablename__ = "car_models"
    id = Column(Integer, primary_key=True, index=True)
    vin = Column(String(17), nullable=False, unique=True, index=True)
    brand = Column(String, nullable=False)
    model = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    engine = Column(String, nullable=True)
    transmission = Column(String, nullable=True)
    drive = Column(String, nullable=True)
    
    user_cars = relationship("UserCar", back_populates="car_model")

class UserCar(Base):
    __tablename__ = "user_cars"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    car_model_id = Column(Integer, ForeignKey("car_models.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="user_cars")
    car_model = relationship("CarModel", back_populates="user_cars")
