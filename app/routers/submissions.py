from fastapi import APIRouter, Request, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from pathlib import Path
import shutil, time

from app.db import engine
from app.models import Submission, Problem, User
from app.auth import get_current_user

router = APIRouter(prefix="/submissions", tags=["submissions"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

@router.get("/", response_class=HTMLResponse)
def list_submissions(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    with Session(engine) as session:
        # Join กับ Problem และ User เพื่อดึงชื่อ problem และชื่อ user ปัจจุบัน
        subs = session.exec(
            select(Submission, Problem.title, User.display_name)
            .join(Problem, Submission.problem_id == Problem.id)
            .join(User, Submission.user_id == User.id)
            .order_by(Submission.id.desc())
        ).all()
        
        # แปลงเป็น list ของ dictionaries
        submissions_with_titles = []
        for sub, title, current_display_name in subs:
            sub_dict = sub.__dict__.copy()
            sub_dict['problem_title'] = title
            sub_dict['current_display_name'] = current_display_name
            submissions_with_titles.append(sub_dict)
    
    return templates.TemplateResponse("submissions.html", {
        "request": request, 
        "submissions": submissions_with_titles,
        "user": current_user
    })

@router.get("/my", response_class=HTMLResponse)
def my_submissions(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    with Session(engine) as session:
        # Join กับ Problem เพื่อดึงชื่อ problem
        subs = session.exec(
            select(Submission, Problem.title)
            .join(Problem, Submission.problem_id == Problem.id)
            .where(Submission.user_id == current_user.id)
            .order_by(Submission.id.desc())
        ).all()
        
        # แปลงเป็น list ของ dictionaries
        submissions_with_titles = []
        for sub, title in subs:
            sub_dict = sub.__dict__.copy()
            sub_dict['problem_title'] = title
            submissions_with_titles.append(sub_dict)
    
    return templates.TemplateResponse("my_submissions.html", {
        "request": request, 
        "submissions": submissions_with_titles,
        "user": current_user
    })

@router.get("/{submission_id}", response_class=HTMLResponse)
def submission_detail(request: Request, submission_id: int, current_user: User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    with Session(engine) as session:
        submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # ตรวจสอบว่า user เป็นเจ้าของ submission หรือเป็นแอดมิน
    if submission.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # อ่าน source code จากไฟล์
    source_code = ""
    if submission.source_path and Path(submission.source_path).exists():
        try:
            source_code = Path(submission.source_path).read_text(encoding='utf-8')
        except Exception as e:
            source_code = f"Error reading source code: {str(e)}"
    
    return templates.TemplateResponse("submission_detail.html", {
        "request": request, 
        "submission": submission,
        "source_code": source_code,
        "user": current_user
    })

@router.post("/{submission_id}/rerun")
async def rerun_submission(
    request: Request,
    submission_id: int,
    current_user: User = Depends(get_current_user)
):
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can rerun submissions")
    
    with Session(engine) as session:
        submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # รีเซ็ตสถานะ submission
    with Session(engine) as session:
        submission = session.get(Submission, submission_id)
        submission.status = "queued"
        submission.score = 0
        submission.tests_passed = 0
        submission.execution_time_ms = 0
        session.add(submission)
        session.commit()
    
    # ส่งไปยัง judge queue (จะต้องมีระบบ queue จริง)
    # สำหรับตอนนี้แค่เปลี่ยนสถานะเป็น queued
    
    return RedirectResponse(url=f"/submissions/{submission_id}", status_code=303)

@router.post("/submit")
async def submit(
    request: Request,
    problem_id: int = Form(...),
    language: str = Form(...),
    source: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    lang = language.strip().lower()
    if lang not in {"c", "cpp"}:
        raise HTTPException(status_code=400, detail="language must be 'c' or 'cpp'")

    with Session(engine) as session:
        problem = session.get(Problem, problem_id)
        if not problem:
            return HTMLResponse("Problem not found", status_code=404)
        
        sub = Submission(
            problem_id=problem_id, 
            user_id=current_user.id,
            user_name=current_user.display_name,
            language=lang, 
            source_path="",
            max_score=problem.max_score
        )
        session.add(sub)
        session.commit()
        session.refresh(sub)
        
        sub_dir = DATA_DIR / "submissions" / str(sub.id)
        sub_dir.mkdir(parents=True, exist_ok=True)
        # ปรับชื่อไฟล์ตามภาษา
        ext = ".c" if lang == "c" else ".cpp"
        dest = sub_dir / (Path(source.filename).stem + ext)
        data = await source.read()
        dest.write_bytes(data)
        sub.source_path = str(dest)
        session.add(sub)
        session.commit()
    
    return RedirectResponse(url="/submissions/", status_code=303)