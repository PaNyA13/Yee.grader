from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from pathlib import Path
import zipfile, io, re, aiofiles, os
import PyPDF2

from app.db import engine
from app.models import Problem, User, Submission
from app.auth import get_current_user

router = APIRouter(prefix="/problems", tags=["problems"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

@router.get("/", response_class=HTMLResponse)
def list_problems(request: Request, current_user: User = Depends(get_current_user), search: str = ""):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    with Session(engine) as session:
        # สร้าง query พื้นฐาน
        query = select(Problem)
        
        # เพิ่มเงื่อนไข search ถ้ามี
        if search.strip():
            query = query.where(Problem.title.contains(search.strip()))
        
        problems = session.exec(query.order_by(Problem.id.desc())).all()
        
        # เพิ่มข้อมูลสถานะการทำของแต่ละโจทย์สำหรับ user ปัจจุบัน
        problems_with_status = []
        for problem in problems:
            # หา submission ที่ดีที่สุดของ user นี้สำหรับโจทย์นี้
            best_submission = session.exec(
                select(Submission)
                .where(Submission.user_id == current_user.id, Submission.problem_id == problem.id)
                .order_by(Submission.score.desc())
            ).first()
            
            problem_dict = {
                'id': problem.id,
                'title': problem.title,
                'max_score': problem.max_score,
                'testcase_count': problem.testcase_count,
                'pdf_path': problem.pdf_path,
                'description': problem.description,
                'time_limit_ms': problem.time_limit_ms,
                'memory_limit_mb': problem.memory_limit_mb,
                'status': 'not_attempted'  # default
            }
            
            if best_submission:
                if best_submission.score == problem.max_score:
                    problem_dict['status'] = 'solved'
                elif best_submission.score > 0:
                    problem_dict['status'] = 'partial'
                else:
                    problem_dict['status'] = 'failed'
            
            problems_with_status.append(problem_dict)
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "problems": problems_with_status,
        "user": current_user,
        "search_query": search.strip()
    })

@router.get("/upload", response_class=HTMLResponse)
def upload_form(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can upload problems")
    
    return templates.TemplateResponse("upload_problem.html", {
        "request": request,
        "user": current_user
    })

@router.post("/upload")
async def upload_problem(
    request: Request,
    title: str = Form(...),
    slug: str = Form(...),
    description: str = Form(""),
    time_limit_ms: int = Form(2000),
    memory_limit_mb: int = Form(256),
    max_score: int = Form(100),
    problem_pdf: UploadFile = File(...),
    testcases_zip: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can upload problems")
    
    slug = re.sub(r"[^a-z0-9-]", "-", slug.lower())
    
    # บันทึก PDF
    pdf_path = DATA_DIR / "pdfs" / f"{slug}.pdf"
    async with aiofiles.open(pdf_path, 'wb') as f:
        content = await problem_pdf.read()
        await f.write(content)
    
    # นับจำนวน testcases (ดูจาก basename เพื่อรองรับโฟลเดอร์ซ้อน)
    data = await testcases_zip.read()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        basenames = [os.path.basename(n) for n in names if not n.endswith("/")]
        input_files = [n for n in basenames if n.startswith('input') and n.endswith('.txt')]
        output_files = [n for n in basenames if n.startswith('output') and n.endswith('.txt')]
        testcase_count = min(len(input_files), len(output_files))
    
    with Session(engine) as session:
        problem = Problem(
            title=title, 
            slug=slug, 
            description=description,
            pdf_path=str(pdf_path),
            time_limit_ms=time_limit_ms, 
            memory_limit_mb=memory_limit_mb,
            max_score=max_score,
            testcase_count=testcase_count
        )
        session.add(problem)
        session.commit()
        session.refresh(problem)
        
        # บันทึก testcases
        prob_dir = DATA_DIR / "problems" / str(problem.id)
        prob_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(prob_dir)
    
    return RedirectResponse(url=f"/problems/{problem.id}", status_code=303)

@router.get("/{problem_id}", response_class=HTMLResponse)
def problem_detail(problem_id: int, request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    with Session(engine) as session:
        problem = session.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return templates.TemplateResponse("problem_detail.html", {
        "request": request, 
        "problem": problem,
        "user": current_user
    })

@router.get("/{problem_id}/edit-testcases", response_class=HTMLResponse)
def edit_testcases_form(request: Request, problem_id: int, current_user: User = Depends(get_current_user)):
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can edit testcases")
    
    with Session(engine) as session:
        problem = session.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    return templates.TemplateResponse("edit_testcases.html", {
        "request": request, 
        "problem": problem,
        "user": current_user
    })

@router.post("/{problem_id}/edit-testcases")
async def edit_testcases(
    request: Request,
    problem_id: int,
    testcases_zip: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can edit testcases")
    
    with Session(engine) as session:
        problem = session.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # อัปเดต testcases
    testcase_dir = DATA_DIR / "problems" / str(problem_id)
    testcase_dir.mkdir(parents=True, exist_ok=True)
    
    # ลบ testcases เก่า
    import shutil
    if (testcase_dir / "testcases").exists():
        shutil.rmtree(testcase_dir / "testcases")
    
    # เก็บ testcases ใหม่
    with zipfile.ZipFile(io.BytesIO(await testcases_zip.read()), 'r') as zip_ref:
        zip_ref.extractall(testcase_dir / "testcases")
    
    # นับจำนวน testcases
    testcase_count = len([f for f in (testcase_dir / "testcases").iterdir() if f.suffix == '.in'])
    
    # อัปเดตข้อมูลในฐานข้อมูล
    with Session(engine) as session:
        problem = session.get(Problem, problem_id)
        problem.testcase_count = testcase_count
        session.add(problem)
        session.commit()
    
    return RedirectResponse(url=f"/problems/{problem_id}", status_code=303)

@router.get("/{problem_id}/pdf")
def get_pdf(problem_id: int, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    with Session(engine) as session:
        problem = session.get(Problem, problem_id)
    if not problem or not problem.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(problem.pdf_path, media_type="application/pdf")