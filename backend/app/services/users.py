"""
Truy vấn bảng users (SQLite).
"""
import math
import sqlite3
import unicodedata
from typing import Any

from app.db import get_db


def _username_lookup_variants(login: str) -> list[str]:
    """Các dạng MSSV tương đương (legacy import Excel lưu nhầm '20210001.0')."""
    q = unicodedata.normalize("NFKC", (login or "").strip())
    if not q:
        return []
    out: list[str] = []
    seen: set[str] = set()

    def add(s: str) -> None:
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    add(q)
    try:
        f = float(q)
        if math.isfinite(f) and f == int(f):
            add(str(int(f)))
    except ValueError:
        pass
    if len(q) > 2 and q.endswith(".0"):
        head = q[:-2]
        if head.isdigit():
            add(head)
    # Legacy Excel số: DB có thể lưu "20210001.0" trong khi SV nhập "20210001"
    if q.isdigit():
        add(q + ".0")
    return out


def find_by_username(conn: sqlite3.Connection, login: str) -> sqlite3.Row | None:
    for key in _username_lookup_variants(login):
        cur = conn.execute("SELECT * FROM users WHERE username = ?", (key,))
        row = cur.fetchone()
        if row:
            return row
    return None


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    cur = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cur.fetchone()


def row_to_public(row: sqlite3.Row) -> dict[str, Any]:
    cid = row["class_id"]
    role = row["role"]
    must = bool(row["must_change_password"])
    if role == "teacher":
        must = False
    return {
        "id": row["id"],
        "username": row["username"],
        "full_name": row["full_name"] or "",
        "role": role,
        "class_id": int(cid) if cid is not None else None,
        "must_change_password": must,
    }


def upsert_user(
    conn: sqlite3.Connection,
    *,
    username: str,
    password_hash: str,
    full_name: str,
    role: str,
    class_id: int | None = None,
    must_change_password: bool = True,
) -> int:
    """INSERT hoặc cập nhật theo username (nạp từ Admin / Excel)."""
    must = 1 if must_change_password else 0
    un = unicodedata.normalize("NFKC", username.strip())
    fn = (full_name or "").strip() or un
    uid: int | None = None
    for key in _username_lookup_variants(un):
        cur = conn.execute("SELECT id FROM users WHERE username = ?", (key,))
        row = cur.fetchone()
        if row:
            uid = int(row["id"])
            break
    if uid is not None:
        conn.execute(
            """
            UPDATE users SET username = ?, password_hash = ?, full_name = ?, role = ?,
                class_id = ?, must_change_password = ?
            WHERE id = ?
            """,
            (un, password_hash, fn, role, class_id, must, uid),
        )
        return uid
    cur = conn.execute(
        """
        INSERT INTO users (username, password_hash, full_name, role, class_id, must_change_password)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (un, password_hash, fn, role, class_id, must),
    )
    return int(cur.lastrowid)


def set_password(
    conn: sqlite3.Connection,
    user_id: int,
    password_hash: str,
    *,
    clear_must_change: bool,
) -> None:
    if clear_must_change:
        conn.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
            (password_hash, user_id),
        )
    else:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (password_hash, user_id),
        )


def seed_demo_users_if_empty(default_password_hash: str) -> None:
    """Thêm lớp + user mẫu khi DB chưa có user (môi trường dev)."""
    from app.services.classes_repo import ensure_class

    with get_db() as conn:
        cur = conn.execute("SELECT COUNT(*) AS c FROM users")
        if cur.fetchone()["c"] > 0:
            return
        class_id = ensure_class(
            conn,
            class_name="KTPM — Demo",
            department="Khoa Công nghệ thông tin",
        )
        upsert_user(
            conn,
            username="38165",
            password_hash=default_password_hash,
            full_name="Sinh viên Demo",
            role="student",
            class_id=class_id,
            must_change_password=True,
        )
        upsert_user(
            conn,
            username="gv.demo",
            password_hash=default_password_hash,
            full_name="Giảng viên Demo",
            role="teacher",
            class_id=None,
            must_change_password=False,
        )
