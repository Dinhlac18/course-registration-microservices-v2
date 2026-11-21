import os
import sqlite3
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, model_validator

app = FastAPI(title="Registration Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "/tmp/registrations.db" if os.getenv("VERCEL") else "registrations.db"
STUDENT_SERVICE_URL = os.getenv("STUDENT_SERVICE_URL", "")
COURSE_SERVICE_URL = os.getenv("COURSE_SERVICE_URL", "")


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_code TEXT NOT NULL,
                section_code TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'REGISTERED',
                UNIQUE(student_code, section_code)
            )
            """
        )


init_db()


class RegistrationCreate(BaseModel):
    student_code: str
    section_code: str
    status: Optional[str] = "REGISTERED"

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data):
        if isinstance(data, dict):
            if not data.get("section_code"):
                data["section_code"] = (
                    data.get("course_code")
                    or data.get("class_code")
                    or data.get("section_id")
                    or ""
                )
            if not data.get("student_code"):
                raw_student = data.get("student_id")
                data["student_code"] = str(raw_student) if raw_student is not None else ""
        return data


class RegistrationUpdate(BaseModel):
    status: str


def _list_registrations(student_code: Optional[str] = None):
    with get_db() as conn:
        if student_code and student_code.strip():
            rows = conn.execute(
                "SELECT * FROM registrations WHERE student_code = ? ORDER BY id DESC",
                (student_code.strip(),),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM registrations ORDER BY id DESC"
            ).fetchall()
        return [dict(r) for r in rows]


def _create_registration(data: RegistrationCreate):
    student_code = data.student_code.strip()
    section_code = data.section_code.strip()
    status = (data.status or "REGISTERED").strip()
    if not student_code or not section_code:
        raise HTTPException(
            status_code=422, detail="Vui lòng nhập mã sinh viên và mã lớp học phần"
        )

    with get_db() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO registrations (student_code, section_code, status)
                VALUES (?, ?, ?)
                """,
                (student_code, section_code, status),
            )
            row = conn.execute(
                "SELECT * FROM registrations WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            return dict(row)
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=400, detail="Sinh viên đã đăng ký lớp học phần này"
            )


def _update_registration(reg_id: int, data: RegistrationUpdate):
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE registrations SET status = ? WHERE id = ?",
            (data.status.strip(), reg_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy lượt đăng ký")
        row = conn.execute(
            "SELECT * FROM registrations WHERE id = ?", (reg_id,)
        ).fetchone()
        return dict(row)


def _delete_registration(reg_id: int):
    with get_db() as conn:
        cur = conn.execute("DELETE FROM registrations WHERE id = ?", (reg_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy lượt đăng ký")
        return {"deleted": True, "id": reg_id}


@app.get("/health")
@app.get("/api/registrations/health")
def health():
    return {
        "service": "registration-service",
        "status": "ok",
        "student_service_configured": bool(STUDENT_SERVICE_URL),
        "course_service_configured": bool(COURSE_SERVICE_URL),
    }


@app.get("/registrations")
@app.get("/registrations/")
@app.get("/api/registrations")
@app.get("/api/registrations/")
@app.get("/api/registrations/registrations")
@app.get("/api/registrations/registrations/")
def list_registrations(student_code: Optional[str] = Query(default=None)):
    return _list_registrations(student_code)


@app.post("/registrations", status_code=201)
@app.post("/registrations/", status_code=201)
@app.post("/api/registrations", status_code=201)
@app.post("/api/registrations/", status_code=201)
@app.post("/api/registrations/registrations", status_code=201)
@app.post("/api/registrations/registrations/", status_code=201)
def create_registration(data: RegistrationCreate):
    return _create_registration(data)


@app.put("/registrations/{reg_id}")
@app.put("/api/registrations/{reg_id}")
@app.put("/api/registrations/registrations/{reg_id}")
@app.patch("/registrations/{reg_id}")
@app.patch("/api/registrations/{reg_id}")
@app.patch("/api/registrations/registrations/{reg_id}")
def update_registration(reg_id: int, data: RegistrationUpdate):
    return _update_registration(reg_id, data)


@app.delete("/registrations/{reg_id}")
@app.delete("/api/registrations/{reg_id}")
@app.delete("/api/registrations/registrations/{reg_id}")
def delete_registration(reg_id: int):
    return _delete_registration(reg_id)