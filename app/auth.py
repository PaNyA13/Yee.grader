from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from pathlib import Path
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

from app.db import engine
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Predefined users
PREDEFINED_USERS = {
    "yee": {"password": "yee", "is_admin": True},
    "user01": {"password": "q7k2f", "is_admin": False},
    "user02": {"password": "d9t4x", "is_admin": False},
    "user03": {"password": "a1z8m", "is_admin": False},
    "user04": {"password": "w4e7r", "is_admin": False},
    "user05": {"password": "j6b3q", "is_admin": False},
    "user06": {"password": "t9h2c", "is_admin": False},
    "user07": {"password": "y5n8u", "is_admin": False},
    "user08": {"password": "l0p4k", "is_admin": False},
    "user09": {"password": "b3x6z", "is_admin": False},
    "user10": {"password": "v8r1j", "is_admin": False},
    "user11": {"password": "k2m9t", "is_admin": False},
    "user12": {"password": "z7y4d", "is_admin": False},
    "user13": {"password": "c5h8s", "is_admin": False},
    "user14": {"password": "g9w3p", "is_admin": False},
    "user15": {"password": "r1t7n", "is_admin": False},
    "user16": {"password": "n4u6v", "is_admin": False},
    "user17": {"password": "f2q5m", "is_admin": False},
    "user18": {"password": "x0d9c", "is_admin": False},
    "user19": {"password": "s8b1y", "is_admin": False},
    "user20": {"password": "h3j6l", "is_admin": False},
    "user21": {"password": "p5v2a", "is_admin": False},
    "user22": {"password": "o7k9r", "is_admin": False},
    "user23": {"password": "e1x4z", "is_admin": False},
    "user24": {"password": "m8n3t", "is_admin": False},
    "user25": {"password": "d6f7q", "is_admin": False},
    "user26": {"password": "j0y2c", "is_admin": False},
    "user27": {"password": "l9p5b", "is_admin": False},
    "user28": {"password": "u4r7x", "is_admin": False},
    "user29": {"password": "t6h8s", "is_admin": False},
    "user30": {"password": "a3k1n", "is_admin": False},
    "user31": {"password": "w5d2j", "is_admin": False},
    "user32": {"password": "q7v9l", "is_admin": False},
    "user33": {"password": "z8y4m", "is_admin": False},
    "user34": {"password": "c0n6t", "is_admin": False},
    "user35": {"password": "f2r3p", "is_admin": False},
    "user36": {"password": "k9h1u", "is_admin": False},
    "user37": {"password": "g5b7x", "is_admin": False},
    "user38": {"password": "n4w8z", "is_admin": False},
    "user39": {"password": "y3q2d", "is_admin": False},
    "user40": {"password": "o6j9c", "is_admin": False},
    "user41": {"password": "e7m1t", "is_admin": False},
    "user42": {"password": "l2p4s", "is_admin": False},
    "user43": {"password": "t8x0v", "is_admin": False},
    "user44": {"password": "d9k3q", "is_admin": False},
    "user45": {"password": "h1y5n", "is_admin": False},
    "user46": {"password": "r6f2j", "is_admin": False},
    "user47": {"password": "m7c9u", "is_admin": False},
    "user48": {"password": "b4z8t", "is_admin": False},
    "user49": {"password": "p0n3k", "is_admin": False},
    "user50": {"password": "v2w6y", "is_admin": False},
}

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user_by_username(username: str):
    with Session(engine) as session:
        return session.exec(select(User).where(User.username == username)).first()

def authenticate_user(username: str, password: str):
    user = get_user_by_username(username)
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user

def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return get_user_by_username(username)
    except JWTError:
        return None

def init_users():
    with Session(engine) as session:
        for username, data in PREDEFINED_USERS.items():
            existing = session.exec(select(User).where(User.username == username)).first()
            if not existing:
                user = User(
                    username=username,
                    password_hash=get_password_hash(data["password"]),
                    display_name=username,
                    is_admin=data["is_admin"]
                )
                session.add(user)
        session.commit()

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("login.html", {"request": request, "user": user})

@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "user": None,
            "error": "Invalid username or password"
        })
    
    access_token = create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@router.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token")
    return response

@router.get("/profile", response_class=HTMLResponse)
def profile(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    return templates.TemplateResponse("profile.html", {
        "request": request, 
        "user": current_user
    })

@router.post("/change-name")
def change_name(
    request: Request, 
    new_name: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    if current_user.name_changes_left <= 0:
        return templates.TemplateResponse("profile.html", {
            "request": request,
            "user": current_user,
            "error": "No name changes left"
        })
    
    with Session(engine) as session:
        user = session.get(User, current_user.id)
        user.display_name = new_name
        user.name_changes_left -= 1
        session.add(user)
        session.commit()
    
    return RedirectResponse(url="/auth/profile", status_code=303)