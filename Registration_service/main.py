import json
import os
import sqlite3
from typing import Optional
from urllib import error, request
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
STUDENT_SERVICE_URL = os.getenv("STUDENT_SERVICE_URL", "").rstrip("/")
COURSE_SERVICE_URL = os.getenv("COURSE_SERVICE_URL", "").rstrip("/")
PUBLIC_BASE_URL = "https://course-registration-microservices-v-navy.vercel.app"


def _get_course_base_url() -> str:
    if COURSE_SERVICE_URL:
        return COURSE_SERVICE_URL
    if os.getenv("VERCEL"):
        return f"{PUBLIC_BASE_URL}/api/courses"
    return "http://127.0.0.1:8002"


def _count_registrations_for_section(conn, section_id: Optional[int]) -> int:
    if section_id is None:
        return 0
    row = conn.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM registrations
        WHERE section_id = ? OR section_code = ?
        """,
        (int(section_id), str(section_id)),
    ).fetchone()
    return int(row["cnt"] if row else 0)


def _sync_exact_enrolled_count(section_id: Optional[int], exact_count: int):
    if section_id is None:
        return
    base = _get_course_base_url().rstrip("/")
    url = f"{base}/sections/{int(section_id)}/set-enrolled"
    payload = json.dumps({"enrolled_slots": max(0, int(exact_count))}).encode("utf-8")
    req = request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=5) as resp:
            if resp.status >= 400:
                raise HTTPException(
                    status_code=resp.status,
                    detail="Không thể đồng bộ sĩ số lớp học phần",
                )
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        detail = "Không thể đồng bộ sĩ số lớp học phần"
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict) and parsed.get("detail"):
                detail = parsed["detail"]
        except Exception:
            pass
        raise HTTPException(status_code=exc.code or 400, detail=detail)
    except Exception:
        pass


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
                section_id INTEGER,
                status TEXT NOT NULL DEFAULT 'REGISTERED',
                UNIQUE(student_code, section_code)
            )
            """
        )
        cols = [
            r["name"] for r in conn.execute("PRAGMA table_info(registrations)").fetchall()
        ]
        if "section_id" not in cols:
            conn.execute("ALTER TABLE registrations ADD COLUMN section_id INTEGER")


init_db()


class RegistrationCreate(BaseModel):
    student_code: str
    section_code: str
    section_id: Optional[int] = None
    status: Optional[str] = "REGISTERED"

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data):
        if isinstance(data, dict):
            raw_section_id = data.get("section_id")
            parsed_section_id = None
            if raw_section_id is not None and str(raw_section_id).strip() != "":
                try:
                    parsed_section_id = int(raw_section_id)
                except (ValueError, TypeError):
                    parsed_section_id = None

            raw_section = data.get("section_code")
            if raw_section is None or str(raw_section).strip() == "":
                raw_section = (
                    data.get("course_code")
                    or data.get("class_code")
                    or (str(parsed_section_id) if parsed_section_id is not None else "")
                    or (str(raw_section_id) if raw_section_id is not None else "")
                )

            raw_student = data.get("student_code")
            if raw_student is None or str(raw_student).strip() == "":
                raw_student = data.get("student_id")

            return {
                **data,
                "student_code": str(raw_student).strip() if raw_student is not None else "",
                "section_code": str(raw_section).strip() if raw_section is not None else "",
                "section_id": parsed_section_id,
                "status": str(data.get("status") or "REGISTERED").strip(),
            }
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
    section_id = data.section_id
    status = (data.status or "REGISTERED").strip() or "REGISTERED"

    if not student_code or not section_code:
        raise HTTPException(
            status_code=422, detail="Vui lòng nhập mã sinh viên và mã lớp học phần"
        )

    with get_db() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO registrations (student_code, section_code, section_id, status)
                VALUES (?, ?, ?, ?)
                """,
                (student_code, section_code, section_id, status),
            )
            row = conn.execute(
                "SELECT * FROM registrations WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            exact_count = _count_registrations_for_section(conn, section_id)
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=400, detail="Sinh viên đã đăng ký lớp học phần này"
            )

    _sync_exact_enrolled_count(section_id, exact_count)
    return dict(row)


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
        existing = conn.execute(
            "SELECT * FROM registrations WHERE id = ?", (reg_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Không tìm thấy lượt đăng ký")

        section_id = existing["section_id"]
        if section_id is None and existing["section_code"]:
            try:
                section_id = int(str(existing["section_code"]).strip())
            except ValueError:
                section_id = None

        conn.execute("DELETE FROM registrations WHERE id = ?", (reg_id,))
        exact_count = _count_registrations_for_section(conn, section_id)

    _sync_exact_enrolled_count(section_id, exact_count)
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


@app.get("/registrations/counts")
@app.get("/registrations/counts/")
@app.get("/api/registrations/counts")
@app.get("/api/registrations/counts/")
@app.get("/api/registrations/registrations/counts")
@app.get("/api/registrations/registrations/counts/")
def registration_counts():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT section_id, section_code, COUNT(*) AS cnt
            FROM registrations
            GROUP BY section_id, section_code
            """
        ).fetchall()
        by_section_id = {}
        for r in rows:
            sid = r["section_id"]
            if sid is None and r["section_code"]:
                try:
                    sid = int(str(r["section_code"]).strip())
                except ValueError:
                    sid = None
            if sid is not None:
                by_section_id[str(sid)] = by_section_id.get(str(sid), 0) + int(r["cnt"])
        return {"counts": by_section_id}


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