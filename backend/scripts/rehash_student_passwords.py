"""
Đặt lại mật khẩu tất cả tài khoản role=student thành DEFAULT_INITIAL_PASSWORD (từ .env / mặc định).

Dùng khi CSDL còn hash cũ (import trước khi đổi quy tắc mật khẩu) nên đăng nhập Huce@123 bị 401.

Chạy từ thư mục backend:
  python scripts/rehash_student_passwords.py
"""
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv

load_dotenv(_BACKEND / ".env")

from app.core.config import DEFAULT_INITIAL_PASSWORD, DATABASE_PATH, PROJECT_ROOT
from app.db import get_db
from app.services.auth_service import hash_password


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass

    h = hash_password(DEFAULT_INITIAL_PASSWORD)
    with get_db() as conn:
        cur = conn.execute(
            """
            UPDATE users
            SET password_hash = ?, must_change_password = 1
            WHERE role = 'student'
            """,
            (h,),
        )
        n = cur.rowcount if cur.rowcount is not None else -1
    print("OK: all student passwords set to", repr(DEFAULT_INITIAL_PASSWORD), "rowcount=", n)
    try:
        rel = DATABASE_PATH.resolve().relative_to(PROJECT_ROOT.resolve())
        print("DB (under project):", rel.as_posix())
    except ValueError:
        print("DB (under project): data/users.db")
    try:
        print("DB (absolute):", DATABASE_PATH.resolve())
    except UnicodeEncodeError:
        pass


if __name__ == "__main__":
    main()
