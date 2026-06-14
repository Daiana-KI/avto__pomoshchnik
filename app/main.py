from fastapi import FastAPI, Request, Form, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud import get_user_by_username, get_user_by_email, create_user, get_user_cars
from app.auth import verify_password, create_access_token
from app.models import CarModel
from app.routers import cars, ask, auth
from app.cache import init_redis, close_redis
from jinja2 import Environment, FileSystemLoader
import os

app = FastAPI(title="Автомобильный помощник")
app.add_middleware(
    SessionMiddleware,
    secret_key="supersecretkey123",
    max_age=86400 * 30,
    https_only=False
)

# Настройка Jinja2 без использования Jinja2Templates
jinja_env = Environment(loader=FileSystemLoader("templates"))

app.include_router(cars.router)
app.include_router(ask.router)
app.include_router(auth.router)

@app.on_event("startup")
async def startup():
    await init_redis()

@app.on_event("shutdown")
async def shutdown():
    await close_redis()

# ----- Страницы -----
@app.get("/", response_class=HTMLResponse)
async def home():
    return RedirectResponse(url="/login")

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    template = jinja_env.get_template("register.html")
    html = template.render({})
    return HTMLResponse(content=html)

@app.post("/register")
async def register(request: Request, username: str = Form(...), email: str = Form(None), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_username(db, username)
    if existing:
        template = jinja_env.get_template("register.html")
        html = template.render({"error": "Логин уже занят"})
        return HTMLResponse(content=html, status_code=400)
    if email:
        existing_email = await get_user_by_email(db, email)
        if existing_email:
            template = jinja_env.get_template("register.html")
            html = template.render({"error": "Email уже используется"})
            return HTMLResponse(content=html, status_code=400)
    await create_user(db, username, email, password)
    return RedirectResponse(url="/login", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    template = jinja_env.get_template("login.html")
    html = template.render({})
    return HTMLResponse(content=html)

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    user = await get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        template = jinja_env.get_template("login.html")
        html = template.render({"error": "Неверный логин или пароль"})
        return HTMLResponse(content=html, status_code=400)
    token = create_access_token(data={"sub": user.username, "user_id": user.id})
    request.session["token"] = token
    request.session["user_id"] = user.id
    return RedirectResponse(url="/profile", status_code=303)

@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    user_cars = await get_user_cars(db, user_id)  # список UserCar
    cars_dict = []
    for uc in user_cars:
        # Загружаем CarModel по car_model_id
        car_model = await db.get(CarModel, uc.car_model_id)
        if car_model:
            cars_dict.append({
                "id": car_model.id,
                "brand": car_model.brand,
                "model": car_model.model,
                "year": car_model.year,
                "engine": car_model.engine,
                "transmission": car_model.transmission,
                "drive": car_model.drive,
                "user_car_id": uc.id  # для удаления/редактирования
            })
    template = jinja_env.get_template("profile.html")
    html = template.render({"cars": cars_dict})
    return HTMLResponse(content=html)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")