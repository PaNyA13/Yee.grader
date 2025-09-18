from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func
from pathlib import Path
from datetime import datetime

from app.db import engine
from app.models import User, Submission, Problem
from app.auth import get_current_user

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

@router.get("/", response_class=HTMLResponse)
def leaderboard(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    with Session(engine) as session:
        # คำนวณคะแนนรวมและจำนวนโจทย์ที่แก้ได้ (ไม่รวม admin)
        stats = session.exec(
            select(
                User.id,
                User.display_name,
                func.sum(Submission.score).label('total_score'),
                func.count(func.distinct(Submission.problem_id)).label('problems_solved'),
                func.count(Submission.id).label('total_submissions')
            )
            .join(Submission, User.id == Submission.user_id)
            .where(Submission.status == "accepted", User.is_admin == False)
            .group_by(User.id, User.display_name)
            .order_by(func.sum(Submission.score).desc())
        ).all()
        
        # แปลง stats เป็น list ของ dictionaries และเพิ่มข้อมูลโจทย์ที่ทำได้
        stats_list = []
        for stat in stats:
            # ดึงเฉพาะปัญหาที่แก้ได้ครั้งแรก (first accepted submission)
            solved_problems = session.exec(
                select(Submission.problem_id, Submission.score, Problem.max_score)
                .join(Problem, Submission.problem_id == Problem.id)
                .where(Submission.user_id == stat.id, Submission.status == "accepted")
                .order_by(Submission.problem_id, Submission.id.asc())
            ).all()
            
            # กรองให้เหลือเฉพาะปัญหาที่แก้ได้ครั้งแรก
            unique_problems = {}
            for problem in solved_problems:
                if problem.problem_id not in unique_problems:
                    unique_problems[problem.problem_id] = problem
            
            solved_problems = list(unique_problems.values())
            
            stat_dict = {
                'id': stat.id,
                'display_name': stat.display_name,
                'total_score': stat.total_score or 0,
                'problems_solved': stat.problems_solved or 0,
                'total_submissions': stat.total_submissions or 0,
                'solved_problems': solved_problems
            }
            stats_list.append(stat_dict)
    
    return templates.TemplateResponse("leaderboard.html", {
        "request": request, 
        "stats": stats_list,
        "user": current_user,
        "current_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })