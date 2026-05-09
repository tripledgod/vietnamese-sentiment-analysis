"""
Bảng feedbacks — nội dung thô + nhãn PhoBERT + độ tin cậy.
"""
import sqlite3
from typing import Any


def insert_feedback(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    content: str,
    label: str,
    confidence: float,
    survey_config_id: int | None = None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO feedbacks (user_id, content, label, confidence, survey_config_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, content, label, float(confidence), survey_config_id),
    )
    return int(cur.lastrowid)


def list_feedbacks_for_dashboard(
    conn: sqlite3.Connection,
    *,
    min_confidence: float = 0.0,
    class_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Danh sách phản hồi kèm thông tin sinh viên (cho giáo viên)."""
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    sql = """
        SELECT
            f.id AS id,
            f.content AS content,
            f.label AS label,
            f.confidence AS confidence,
            f.created_at AS created_at,
            f.user_id AS user_id,
            u.username AS username,
            u.full_name AS student_full_name,
            u.class_id AS student_class_id,
            c.class_name AS class_name,
            c.department AS department
        FROM feedbacks f
        INNER JOIN users u ON u.id = f.user_id
        LEFT JOIN classes c ON c.id = u.class_id
        WHERE f.confidence >= ?
    """
    params: list[Any] = [min_confidence]
    if class_id is not None:
        sql += " AND u.class_id = ?"
        params.append(class_id)
    sql += " ORDER BY f.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def list_feedbacks_by_user(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Các lượt gửi của một sinh viên (mỗi hàng = một lượt, sắp xếp mới nhất trước)."""
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    cur = conn.execute(
        """
        SELECT
            f.id,
            f.user_id,
            f.content,
            f.label,
            f.confidence,
            f.created_at,
            f.survey_config_id,
            s.subject_name AS subject_name,
            sem.name AS semester_name
        FROM feedbacks f
        LEFT JOIN survey_configs sc ON sc.id = f.survey_config_id
        LEFT JOIN subjects s ON s.id = sc.subject_id
        LEFT JOIN semesters sem ON sem.id = sc.semester_id
        WHERE f.user_id = ?
        ORDER BY datetime(f.created_at) DESC, f.id DESC
        LIMIT ? OFFSET ?
        """,
        (user_id, limit, offset),
    )
    return [dict(r) for r in cur.fetchall()]


def count_feedbacks_by_user(conn: sqlite3.Connection, user_id: int) -> int:
    cur = conn.execute(
        "SELECT COUNT(*) AS c FROM feedbacks WHERE user_id = ?",
        (user_id,),
    )
    return int(cur.fetchone()["c"])


def count_feedbacks(
    conn: sqlite3.Connection,
    *,
    min_confidence: float = 0.0,
    class_id: int | None = None,
) -> int:
    sql = """
        SELECT COUNT(*) AS c FROM feedbacks f
        INNER JOIN users u ON u.id = f.user_id
        WHERE f.confidence >= ?
    """
    params: list[Any] = [min_confidence]
    if class_id is not None:
        sql += " AND u.class_id = ?"
        params.append(class_id)
    cur = conn.execute(sql, params)
    return int(cur.fetchone()["c"])
