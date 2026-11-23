import os
import sqlite3
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Course Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "/tmp/courses.db" if os.getenv("VERCEL") else "courses.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT NOT NULL,
                course_name TEXT NOT NULL,
                credits INTEGER NOT NULL DEFAULT 3,
                schedule TEXT NOT NULL,
                max_slots INTEGER NOT NULL DEFAULT 30,
                enrolled_slots INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) AS cnt FROM sections").fetchone()["cnt"]
        if count == 0:
            conn.executemany(
                """
                INSERT INTO sections (course_code, course_name, credits, schedule, max_slots, enrolled_slots)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    ("SE301", "Kiến trúc Microservices", 3, "Thứ 2 ( Tiết 1 - 3 )", 30, 0),
                    ("SE302", "Kiểm thử phần mềm", 3, "Thứ 3 ( Tiết 4 - 6 )", 40, 0),
                    ("SE303", "Toán Cao Cấp", 3, "Thứ 3 ( Tiết 4 - 6 )", 30, 0),
                ],
            )


init_db()


class SectionCreate(BaseModel):
    course_code: str
    course_name: str
    credits: int = 3
    schedule: str
    max_slots: int = 30
    enrolled_slots: Optional[int] = 0


class EnrolledCountUpdate(BaseModel):
    enrolled_slots: int


def _get_section_or_404(conn, section_id: int):
    row = conn.execute("SELECT * FROM sections WHERE id = ?", (section_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học phần")
    return dict(row)


def _set_enrolled(section_id: int, count: int):
    with get_db() as conn:
        sec = _get_section_or_404(conn, section_id)
        max_slots = int(sec["max_slots"] or 30)
        safe_count = max(0, min(int(count), max_slots))
        conn.execute(
            "UPDATE sections SET enrolled_slots = ? WHERE id = ?",
            (safe_count, section_id),
        )
        updated = conn.execute(
            "SELECT * FROM sections WHERE id = ?", (section_id,)
        ).fetchone()
        return dict(updated)


def _adjust_slots(section_id: int, delta: int):
    with get_db() as conn:
        sec = _get_section_or_404(conn, section_id)
        current = int(sec["enrolled_slots"] or 0)
        max_slots = int(sec["max_slots"] or 30)

        if delta > 0 and current + delta > max_slots:
            raise HTTPException(status_code=400, detail="Lớp học phần đã hết chỗ")

        new_val = max(0, current + delta)
        conn.execute(
            "UPDATE sections SET enrolled_slots = ? WHERE id = ?",
            (new_val, section_id),
        )
        updated = conn.execute(
            "SELECT * FROM sections WHERE id = ?", (section_id,)
        ).fetchone()
        return dict(updated)


@app.get("/health")
@app.get("/api/courses/health")
def health():
    return {"service": "course-service", "status": "ok"}


@app.get("/sections")
@app.get("/sections/")
@app.get("/api/courses/sections")
@app.get("/api/courses/sections/")
def list_sections():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM sections ORDER BY id ASC").fetchall()
        return [dict(r) for r in rows]


@app.post("/sections", status_code=201)
@app.post("/sections/", status_code=201)
@app.post("/api/courses/sections", status_code=201)
@app.post("/api/courses/sections/", status_code=201)
def create_section(data: SectionCreate):
    enrolled = max(0, int(data.enrolled_slots or 0))
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO sections (course_code, course_name, credits, schedule, max_slots, enrolled_slots)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data.course_code.strip(),
                data.course_name.strip(),
                int(data.credits),
                data.schedule.strip(),
                int(data.max_slots),
                enrolled,
            ),
        )
        row = conn.execute(
            "SELECT * FROM sections WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return dict(row)


@app.delete("/sections/{section_id}")
@app.delete("/sections/{section_id}/")
@app.delete("/api/courses/sections/{section_id}")
@app.delete("/api/courses/sections/{section_id}/")
def delete_section(section_id: int):
    with get_db() as conn:
        cur = conn.execute("DELETE FROM sections WHERE id = ?", (section_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy lớp học phần")
        return {"deleted": True, "id": section_id}


@app.post("/sections/{section_id}/set-enrolled")
@app.post("/sections/{section_id}/set-enrolled/")
@app.post("/api/courses/sections/{section_id}/set-enrolled")
@app.post("/api/courses/sections/{section_id}/set-enrolled/")
def set_enrolled(section_id: int, data: EnrolledCountUpdate):
    return _set_enrolled(section_id, data.enrolled_slots)


@app.post("/sections/{section_id}/enroll")
@app.post("/sections/{section_id}/enroll/")
@app.post("/api/courses/sections/{section_id}/enroll")
@app.post("/api/courses/sections/{section_id}/enroll/")
def enroll_section(section_id: int):
    return _adjust_slots(section_id, +1)


@app.post("/sections/{section_id}/unenroll")
@app.post("/sections/{section_id}/unenroll/")
@app.post("/api/courses/sections/{section_id}/unenroll")
@app.post("/api/courses/sections/{section_id}/unenroll/")
def unenroll_section(section_id: int):
    return _adjust_slots(section_id, -1)