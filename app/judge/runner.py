import threading
import time
import subprocess
import shutil
from pathlib import Path
from typing import Tuple
from sqlmodel import Session, select, func
from app.db import engine
from app.models import Submission, Problem, User

_runner_started = False

def start_runner(base_data_dir: Path):
    global _runner_started
    if _runner_started:
        return
    _runner_started = True

    t = threading.Thread(target=_loop, args=(base_data_dir,), daemon=True)
    t.start()

def _loop(base_data_dir: Path):
    while True:
        try:
            with Session(engine) as session:
                sub = session.exec(select(Submission).where(Submission.status == "queued").order_by(Submission.id.asc())).first()
                if not sub:
                    time.sleep(0.5)
                    continue
                
                sub.status = "running"
                session.add(sub)
                session.commit()

                ok, status, compile_out, run_out, exec_ms, memory_kb, passed_tests, total_tests = _judge_submission(session, sub, base_data_dir)
                
                # คำนวณคะแนน (ไม่มี penalty)
                if status == "accepted":
                    sub.score = sub.max_score
                elif passed_tests > 0:
                    # Partial scoring
                    sub.score = int((passed_tests / total_tests) * sub.max_score)
                else:
                    sub.score = 0
                
                sub.status = status
                sub.passed_tests = passed_tests
                sub.total_tests = total_tests
                sub.compile_output = compile_out
                sub.run_output = run_out
                sub.exec_time_ms = exec_ms
                sub.memory_used_kb = memory_kb
                session.add(sub)
                session.commit()
                
                # อัปเดต user stats
                if status == "accepted":
                    user = session.get(User, sub.user_id)
                    if user:
                        user.total_score = session.exec(
                            select(func.sum(Submission.score))
                            .where(Submission.user_id == sub.user_id, Submission.status == "accepted")
                        ).first() or 0
                        user.problems_solved = session.exec(
                            select(func.count(func.distinct(Submission.problem_id)))
                            .where(Submission.user_id == sub.user_id, Submission.status == "accepted")
                        ).first() or 0
                        session.add(user)
                        session.commit()
                        
        except Exception as e:
            print(f"Judge error: {e}")
            time.sleep(1)

def _judge_submission(session: Session, sub: Submission, base_data_dir: Path) -> Tuple[bool, str, str, str, int, int, int, int]:
    prob = session.get(Problem, sub.problem_id)
    if not prob:
        return False, "internal_error", "", "problem not found", 0, 0, 0, 0

    prob_dir = base_data_dir / "problems" / str(prob.id)
    inputs = sorted([p for p in prob_dir.rglob("input*.txt")])
    outputs = sorted([p for p in prob_dir.rglob("output*.txt")])
    
    if not inputs or len(inputs) != len(outputs):
        return False, "internal_error", "", "testcases missing or unmatched", 0, 0, 0, 0

    if sub.language == "c":
        exe_path = Path(sub.source_path).with_suffix(".exe")
        cmd_compile = ["gcc", "-O2", "-std=c17", sub.source_path, "-o", str(exe_path)]
        exec_cmd = [str(exe_path)]
    elif sub.language == "cpp":
        exe_path = Path(sub.source_path).with_suffix(".exe")
        cmd_compile = ["g++", "-O2", "-std=c++17", sub.source_path, "-o", str(exe_path)]
        exec_cmd = [str(exe_path)]
    else:
        return False, "compile_error", "", f"Unsupported language: {sub.language}. Only C and C++ are supported.", 0, 0, 0, 0

    compile_out = ""
    if cmd_compile:
        try:
            r = subprocess.run(cmd_compile, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
            compile_out = r.stdout
            if r.returncode != 0:
                return False, "compile_error", compile_out, "", 0, 0, 0, 0
        except Exception as e:
            return False, "compile_error", str(e), "", 0, 0, 0, 0

    passed_tests = 0
    total_tests = len(inputs)
    total_ms = 0
    max_memory_kb = 0
    
    for inp, outp in zip(inputs, outputs):
        with inp.open("rb") as f_in:
            try:
                import psutil
                import os
                
                # เริ่มต้น process และวัด memory
                process = subprocess.Popen(
                    exec_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                
                # ส่ง input และรอผลลัพธ์
                stdout, _ = process.communicate(
                    input=f_in.read(),
                    timeout=max(1, prob.time_limit_ms / 1000.0)
                )
                
                # วัด memory usage
                try:
                    memory_info = process.memory_info()
                    memory_kb = memory_info.rss // 1024  # แปลงเป็น KB
                    max_memory_kb = max(max_memory_kb, memory_kb)
                except:
                    max_memory_kb = max(max_memory_kb, 0)
                
                r = type('Result', (), {
                    'stdout': stdout,
                    'returncode': process.returncode
                })()
                
            except subprocess.TimeoutExpired:
                return False, "time_limit", compile_out, "time limit exceeded", total_ms, max_memory_kb, passed_tests, total_tests
            except Exception as e:
                return False, "runtime_error", compile_out, str(e), total_ms, max_memory_kb, passed_tests, total_tests
        
        output = r.stdout.decode() if isinstance(r.stdout, (bytes, bytearray)) else r.stdout
        expected = outp.read_text()
        
        if output.strip() == expected.strip():
            passed_tests += 1

    if passed_tests == total_tests:
        return True, "accepted", compile_out, "OK", total_ms, max_memory_kb, passed_tests, total_tests
    else:
        return False, "wrong_answer", compile_out, f"Passed {passed_tests}/{total_tests} tests", total_ms, max_memory_kb, passed_tests, total_tests