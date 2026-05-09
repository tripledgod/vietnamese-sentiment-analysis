"""
Bảng classes — lớp hành chính + khoa (theo ERD).
"""
import sqlite3


def ensure_class(
    conn: sqlite3.Connection,
    *,
    class_name: str,
    department: str = "",
) -> int:
    """Tạo lớp nếu chưa có (khớp class_name + department); trả về id."""
    cn = class_name.strip()
    dep = (department or "").strip()
    if not cn:
        raise ValueError("class_name không được rỗng")
    cur = conn.execute(
        "SELECT id FROM classes WHERE class_name = ? AND department = ?",
        (cn, dep),
    )
    row = cur.fetchone()
    if row:
        return int(row["id"])
    cur = conn.execute(
        "INSERT INTO classes (class_name, department) VALUES (?, ?)",
        (cn, dep),
    )
    return int(cur.lastrowid)


def find_class_id_by_name_dept(
    conn: sqlite3.Connection,
    *,
    class_name: str,
    department: str = "",
) -> int | None:
    cn = str(class_name).strip()
    if not cn:
        return None
    dep = (department or "").strip()
    cur = conn.execute(
        "SELECT id FROM classes WHERE class_name = ? AND department = ?",
        (cn, dep),
    )
    row = cur.fetchone()
    return int(row["id"]) if row else None


def get_class_id_numeric(conn: sqlite3.Connection, value: int) -> int | None:
    cur = conn.execute("SELECT id FROM classes WHERE id = ?", (value,))
    row = cur.fetchone()
    return int(row["id"]) if row else None


def get_class_id_by_class_name(conn: sqlite3.Connection, class_name: str) -> int:
    """
    Tra cứu lớp chỉ theo class_name (khớp y hệt Sheet Classes).
    Lỗi nếu không có hoặc trùng tên ở nhiều dòng (khác department).
    """
    cn = str(class_name).strip()
    if not cn:
        raise ValueError("class_name rỗng")
    cur = conn.execute(
        "SELECT id FROM classes WHERE class_name = ? ORDER BY id",
        (cn,),
    )
    rows = cur.fetchall()
    if not rows:
        raise ValueError(
            f'Không có lớp tên {cn!r}. Thêm dòng tương ứng trong sheet Classes (class_name khớp y hệt).'
        )
    if len(rows) > 1:
        raise ValueError(
            f'Có nhiều lớp cùng tên {cn!r} (khác khoa). Đổi tên hoặc gộp department trên sheet Classes.'
        )
    return int(rows[0]["id"])
