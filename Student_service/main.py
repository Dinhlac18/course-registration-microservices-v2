import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Student Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "/tmp/students.db" if os.getenv("VERCEL") else "students.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_code TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                major TEXT NOT NULL
            )
            """
        )
        seed_students = [
            ("SV001", "Nguyễn Văn An", "Công nghệ thông tin"),
            ("SV002", "Trần Thị Bình", "Kỹ thuật phần mềm"),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO students (student_code, full_name, major) VALUES (?, ?, ?)",
            seed_students,
        )


init_db()


class StudentCreate(BaseModel):
    student_code: str
    full_name: str
    major: str


def _list_students():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM students ORDER BY id ASC").fetchall()
        return [dict(r) for r in rows]


def _get_student(student_code: str):
    code = student_code.strip()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM students WHERE student_code = ?", (code,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên")
        return dict(row)


def _create_student(data: StudentCreate):
    code = data.student_code.strip()
    name = data.full_name.strip()
    major = data.major.strip()
    if not code or not name or not major:
        raise HTTPException(status_code=400, detail="Vui lòng nhập đầy đủ mã SV, họ tên và ngành học")

    with get_db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO students (student_code, full_name, major) VALUES (?, ?, ?)",
                (code, name, major),
            )
            row = conn.execute(
                "SELECT * FROM students WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            return dict(row)
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Mã sinh viên đã tồn tại")


def _delete_student(student_code: str):
    code = student_code.strip()
    with get_db() as conn:
        cur = conn.execute("DELETE FROM students WHERE student_code = ?", (code,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên")
        return {"deleted": True, "student_code": code}


@app.get("/health")
@app.get("/api/students/health")
def health():
    return {"service": "student-service", "status": "ok"}


# Đặt route danh sách trước route động /{student_code} để không bị nhận nhầm "students" là mã SV
@app.get("/students")
@app.get("/students/")
@app.get("/api/students")
@app.get("/api/students/")
@app.get("/api/students/students")
@app.get("/api/students/students/")
def list_students():
    return _list_students()


@app.post("/students", status_code=201)
@app.post("/students/", status_code=201)
@app.post("/api/students", status_code=201)
@app.post("/api/students/", status_code=201)
@app.post("/api/students/students", status_code=201)
@app.post("/api/students/students/", status_code=201)
def create_student(data: StudentCreate):
    return _create_student(data)


@app.get("/students/{student_code}")
@app.get("/api/students/{student_code}")
def get_student(student_code: str):
    return _get_student(student_code)


@app.delete("/students/{student_code}")
@app.delete("/api/students/{student_code}")
def delete_student(student_code: str):
    return _delete_student(student_code)