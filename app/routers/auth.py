import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from app.database import get_db
from app.crud import get_user_by_username, get_user_by_email, create_user
from app.schemas import UserCreate, Token
from app.auth import verify_password, create_access_token, SECRET_KEY, ALGORITHM
from app.models import User
from app.cache import clear_user_cache

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")


# ---------- Регистрация ----------
@router.post("/register", response_model=Token)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_username(db, user.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    new_user = await create_user(db, user)
    access_token = create_access_token(data={"sub": new_user.username, "user_id": new_user.id})
    return {"access_token": access_token, "token_type": "bearer"}

# ---------- Логин ----------
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username, "user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

# ---------- Восстановление пароля ----------
@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_form(request: Request):
    """Страница запроса сброса пароля"""
    return templates.TemplateResponse("forgot_password.html", {"request": request})

@router.post("/forgot-password")
async def forgot_password(email: str = Form(...), db: AsyncSession = Depends(get_db)):
    """Генерирует токен сброса и отправляет email"""
    user = await get_user_by_email(db, email)
    if not user:
        # Не сообщаем, что email не найден (безопасность)
        return RedirectResponse(url="/auth/forgot-password-sent", status_code=303)
    
    # Генерируем токен
    token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(hours=1)
    
    user.reset_token = token
    user.reset_token_expiry = expiry
    await db.commit()
    
    # Здесь в реальном проекте отправляется email
    # Для демо просто показываем токен (в учебном проекте допустимо)
    return RedirectResponse(url=f"/auth/reset-password/{token}", status_code=303)

@router.get("/forgot-password-sent", response_class=HTMLResponse)
async def forgot_password_sent(request: Request):
    """Страница после запроса сброса"""
    return HTMLResponse("""
    <html><body>
    <div class="container mt-5">
        <h3>Ссылка для сброса пароля отправлена</h3>
        <p>Если email зарегистрирован, вы получите ссылку для установки нового пароля.</p>
        <a href="/login">Вернуться ко входу</a>
    </div>
    </body></html>
    """)

@router.get("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_form(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    """Страница установки нового пароля"""
    result = await db.execute(select(User).where(User.reset_token == token))
    user = result.scalar_one_or_none()
    
    if not user or user.reset_token_expiry < datetime.utcnow():
        return HTMLResponse("""
        <html><body>
        <h3>Ссылка недействительна или истекла</h3>
        <a href="/auth/forgot-password">Запросить новую ссылку</a>
        </body></html>
        """, status_code=400)
    
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})

@router.post("/reset-password/{token}")
async def reset_password(token: str, password: str = Form(...), db: AsyncSession = Depends(get_db)):
    """Устанавливает новый пароль"""
    result = await db.execute(select(User).where(User.reset_token == token))
    user = result.scalar_one_or_none()
    
    if not user or user.reset_token_expiry < datetime.utcnow():
        return HTMLResponse("""
        <html><body>
        <h3>Ссылка недействительна или истекла</h3>
        <a href="/auth/forgot-password">Запросить новую ссылку</a>
        </body></html>
        """, status_code=400)
    
    from app.auth import get_password_hash
    user.hashed_password = get_password_hash(password)
    user.reset_token = None
    user.reset_token_expiry = None
    await db.commit()
    
    return RedirectResponse(url="/login", status_code=303)

@router.post("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id:
        await clear_user_cache(user_id)
    request.session.clear()
    return RedirectResponse(url="/login")