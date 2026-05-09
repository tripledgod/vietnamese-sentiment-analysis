"""
Truy vấn thống kê phản hồi cho dashboard giáo viên.
"""
import sqlite3
from typing import Any

VALID_LABELS = frozenset({"positive", "negative", "neutral"})


def count_students_with_feedback(conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        """
        SELECT COUNT(DISTINCT f.user_id) AS c
        FROM feedbacks f
        INNER JOIN users u ON u.id = f.user_id AND u.role = 'student'
        """
    )
    return int(cur.fetchone()["c"])


def count_all_feedbacks(conn: sqlite3.Connection) -> int:
    cur = conn.execute("SELECT COUNT(*) AS c FROM feedbacks")
    return int(cur.fetchone()["c"])


def count_by_label(conn: sqlite3.Connection) -> dict[str, int]:
    cur = conn.execute(
        """
        SELECT label, COUNT(*) AS c
        FROM feedbacks
        GROUP BY label
        """
    )
    out: dict[str, int] = {}
    for row in cur.fetchall():
        out[str(row["label"])] = int(row["c"])
    return out


def class_label_aggregates(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Mỗi dòng: class_id, class_name, department, label, cnt."""
    cur = conn.execute(
        """
        SELECT
            u.class_id AS class_id,
            MAX(COALESCE(c.class_name, 'Chưa phân lớp')) AS class_name,
            MAX(COALESCE(c.department, '')) AS department,
            f.label AS label,
            COUNT(*) AS cnt
        FROM feedbacks f
        INNER JOIN users u ON u.id = f.user_id
        LEFT JOIN classes c ON c.id = u.class_id
        GROUP BY u.class_id, f.label
        """
    )
    return [dict(r) for r in cur.fetchall()]


def list_all_classes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT id, class_name, department
        FROM classes
        ORDER BY department, class_name
        """
    )
    return [dict(r) for r in cur.fetchall()]


def list_feedbacks_admin_filtered(
    conn: sqlite3.Connection,
    *,
    class_id: int | None = None,
    label: str | None = None,
    search_q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[dict[str, Any]]]:
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)

    where = ["1=1"]
    params: list[Any] = []
    if class_id is not None:
        where.append("u.class_id = ?")
        params.append(class_id)
    if label is not None:
        where.append("f.label = ?")
        params.append(label)
    if search_q is not None:
        q = search_q.strip()
        if q:
            where.append("INSTR(LOWER(COALESCE(f.content, '')), LOWER(?)) > 0")
            params.append(q)

    wh = " AND ".join(where)

    cur = conn.execute(
        f"SELECT COUNT(*) AS c FROM feedbacks f INNER JOIN users u ON u.id = f.user_id WHERE {wh}",
        params,
    )
    total = int(cur.fetchone()["c"])

    sql = f"""
        SELECT
            f.id AS id,
            f.content AS content,
            f.label AS label,
            f.confidence AS confidence,
            f.created_at AS created_at,
            f.user_id AS user_id,
            u.username AS username,
            u.full_name AS student_full_name,
            u.class_id AS class_id,
            c.class_name AS class_name,
            c.department AS department
        FROM feedbacks f
        INNER JOIN users u ON u.id = f.user_id
        LEFT JOIN classes c ON c.id = u.class_id
        WHERE {wh}
        ORDER BY datetime(f.created_at) DESC, f.id DESC
        LIMIT ? OFFSET ?
    """
    cur = conn.execute(sql, [*params, limit, offset])
    rows = [dict(r) for r in cur.fetchall()]
    return total, rows


def list_negative_high_confidence(
    conn: sqlite3.Connection,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    limit = min(max(limit, 1), 50)
    cur = conn.execute(
        """
        SELECT
            f.id AS id,
            f.content AS content,
            f.confidence AS confidence,
            f.created_at AS created_at,
            f.user_id AS user_id,
            u.username AS username,
            u.full_name AS student_full_name,
            u.class_id AS class_id,
            c.class_name AS class_name,
            c.department AS department
        FROM feedbacks f
        INNER JOIN users u ON u.id = f.user_id
        LEFT JOIN classes c ON c.id = u.class_id
        WHERE f.label = 'negative'
        ORDER BY f.confidence DESC, datetime(f.created_at) DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(r) for r in cur.fetchall()]


def get_user_profile_row(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    cur = conn.execute(
        """
        SELECT
            u.id AS id,
            u.username AS username,
            u.full_name AS full_name,
            u.role AS role,
            u.class_id AS class_id,
            u.must_change_password AS must_change_password,
            c.class_name AS class_name,
            c.department AS department
        FROM users u
        LEFT JOIN classes c ON c.id = u.class_id
        WHERE u.id = ?
        """,
        (user_id,),
    )
    return cur.fetchone()
