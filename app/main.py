from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
import traceback
from app.routers import problems, submissions, leaderboard
from app import auth
from app.db import init_db
from app.judge.runner import start_runner
from app.models import User

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
(DATA_DIR / "problems").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "submissions").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "pdfs").mkdir(parents=True, exist_ok=True)

app = FastAPI(title="CP Grader with PDF & Scoring & Auth")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(submissions.router)
app.include_router(leaderboard.router)

@app.on_event("startup")
async def on_startup():
    init_db()
    from app.auth import init_users
    init_users()
    start_runner(DATA_DIR)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Global exception: {exc}")
    print(traceback.format_exc())
    return HTMLResponse(f"Internal Server Error: {str(exc)}", status_code=500)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(auth.get_current_user)):
    try:
        return templates.TemplateResponse("index.html", {"request": request, "user": user})
    except Exception as e:
        print(f"Index error: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))