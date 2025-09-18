from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    password_hash: str
    display_name: str
    name_changes_left: int = 2
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Problem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    slug: str
    description: Optional[str] = None
    pdf_path: Optional[str] = None
    time_limit_ms: int = 2000
    memory_limit_mb: int = 256
    max_score: int = 100
    testcase_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Submission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    problem_id: int
    user_id: int
    user_name: str
    language: str  # "c" | "cpp"
    source_path: str
    status: str = "queued"  # queued | running | accepted | wrong_answer | runtime_error | time_limit | compile_error | internal_error
    score: int = 0
    max_score: int = 100
    passed_tests: int = 0
    total_tests: int = 0
    compile_output: Optional[str] = None
    run_output: Optional[str] = None
    exec_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)