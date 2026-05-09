"""
Kỳ học, môn học, cấu hình khảo sát theo lớp (survey_configs).
"""
import sqlite3
from typing import Any


def list_semesters(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute("SELECT id, name FROM semesters ORDER BY id")
    return [dict(r) for r in cur.fetchall()]


def list_subjects_for_semester(conn: sqlite3.Connection, semester_id: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT s.id, s.subject_name, s.subject_code
        FROM subjects s
        INNER JOIN semester_subjects ss ON ss.subject_id = s.id
        WHERE ss.semester_id = ?
        ORDER BY s.subject_name
        """,
        (semester_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def list_classes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT id, class_name, department FROM classes ORDER BY class_name"
    )
    return [dict(r) for r in cur.fetchall()]


def get_survey_config_row(
    conn: sqlite3.Connection, config_id: int
) -> dict[str, Any] | None:
    cur = conn.execute(
        """
        SELECT sc.id, sc.class_id, sc.semester_id, sc.subject_id, sc.is_active
        FROM survey_configs sc
        WHERE sc.id = ?
        """,
        (config_id,),
    )
    r = cur.fetchone()
    return dict(r) if r else None


def assert_config_active_for_class(
    conn: sqlite3.Connection, *, config_id: int, student_class_id: int
) -> dict[str, Any] | None:
    cur = conn.execute(
        """
        SELECT sc.id, sc.class_id, sc.semester_id, sc.subject_id, sc.is_active
        FROM survey_configs sc
        WHERE sc.id = ?
          AND sc.class_id = ?
          AND sc.is_active = 1
        """,
        (config_id, student_class_id),
    )
    r = cur.fetchone()
    return dict(r) if r else None


def list_active_offerings_for_class(
    conn: sqlite3.Connection, class_id: int
) -> list[dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT
            sc.id AS survey_config_id,
            s.subject_name,
            s.subject_code,
            sem.name AS semester_name,
            sem.id AS semester_id
        FROM survey_configs sc
        INNER JOIN subjects s ON s.id = sc.subject_id
        INNER JOIN semesters sem ON sem.id = sc.semester_id
        WHERE sc.class_id = ? AND sc.is_active = 1
        ORDER BY sem.name, s.subject_name
        """,
        (class_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def list_active_offerings_for_student(
    conn: sqlite3.Connection, *, class_id: int, user_id: int
) -> list[dict[str, Any]]:
    """
    Môn đang mở khảo sát cho lớp, trừ những môn sinh viên đã gửi ít nhất một phản hồi
    (feedbacks.survey_config_id khớp).
    """
    cur = conn.execute(
        """
        SELECT
            sc.id AS survey_config_id,
            s.subject_name,
            s.subject_code,
            sem.name AS semester_name,
            sem.id AS semester_id
        FROM survey_configs sc
        INNER JOIN subjects s ON s.id = sc.subject_id
        INNER JOIN semesters sem ON sem.id = sc.semester_id
        WHERE sc.class_id = ? AND sc.is_active = 1
          AND NOT EXISTS (
            SELECT 1 FROM feedbacks f
            WHERE f.user_id = ?
              AND f.survey_config_id = sc.id
          )
        ORDER BY sem.name, s.subject_name
        """,
        (class_id, user_id),
    )
    return [dict(r) for r in cur.fetchall()]


def list_configs_for_class_semester(
    conn: sqlite3.Connection, *, class_id: int, semester_id: int
) -> list[dict[str, Any]]:
    """
    Mỗi môn thuộc kỳ: có survey_config (is_active) hoặc mặc định is_active=0 nếu chưa có dòng.
    """
    subjects = list_subjects_for_semester(conn, semester_id)
    out: list[dict[str, Any]] = []
    for sub in subjects:
        sid = int(sub["id"])
        cur = conn.execute(
            """
            SELECT id, is_active FROM survey_configs
            WHERE class_id = ? AND semester_id = ? AND subject_id = ?
            """,
            (class_id, semester_id, sid),
        )
        row = cur.fetchone()
        if row:
            out.append(
                {
                    "subject_id": sid,
                    "subject_name": sub["subject_name"],
                    "subject_code": sub["subject_code"],
                    "survey_config_id": int(row["id"]),
                    "is_active": bool(row["is_active"]),
                }
            )
        else:
            out.append(
                {
                    "subject_id": sid,
                    "subject_name": sub["subject_name"],
                    "subject_code": sub["subject_code"],
                    "survey_config_id": None,
                    "is_active": False,
                }
            )
    return out


def upsert_survey_activation(
    conn: sqlite3.Connection,
    *,
    class_id: int,
    semester_id: int,
    active_subject_ids: set[int],
) -> None:
    subjects = list_subjects_for_semester(conn, semester_id)
    valid_ids = {int(s["id"]) for s in subjects}
    for sid in active_subject_ids:
        if sid not in valid_ids:
            raise ValueError(f"subject_id={sid} không thuộc kỳ đã chọn")

    for sub in subjects:
        sid = int(sub["id"])
        active = 1 if sid in active_subject_ids else 0
        conn.execute(
            """
            INSERT INTO survey_configs (class_id, semester_id, subject_id, is_active)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(class_id, semester_id, subject_id)
            DO UPDATE SET is_active = excluded.is_active
            """,
            (class_id, semester_id, sid, active),
        )
