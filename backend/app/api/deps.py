"""
JWT Bearer và kiểm tra quyền gọi phân tích cảm xúc.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt as pyjwt

from app.db import get_db
from app.services.auth_service import decode_access_token
from app.services.users import get_user_by_id, row_to_public

security = HTTPBearer(auto_error=False)


def get_predictor_for_inference():
    """PhoBERT đã load trong lifespan — import lười để luôn đọc đúng `predictor_holder` (tránh bản sao module)."""
    from app.core import predictor_holder as ph

    return ph.get_held_predictor()


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict:
    if creds is None or (creds.scheme or "").lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu hoặc sai định dạng Authorization Bearer",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = creds.credentials
    try:
        payload = decode_access_token(token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token thiếu sub")

    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token sub không hợp lệ")

    with get_db() as conn:
        row = get_user_by_id(conn, user_id)
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Người dùng không tồn tại")

    data = row_to_public(row)
    # Đồng bộ cờ đổi mật khẩu với DB (sau khi đổi mật khẩu token cũ vẫn có thể còn mcp=1)
    data["must_change_password"] = bool(row["must_change_password"])
    return data


def require_password_changed(
    user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    if user.get("must_change_password"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vui lòng đổi mật khẩu trước khi sử dụng phân tích cảm xúc",
        )
    return user


def require_model_access(
    user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Sinh viên phải đổi mật khẩu lần đầu; giáo viên dùng tài khoản tạo sẵn, không bắt buộc."""
    if user.get("role") == "teacher":
        return user
    if user.get("must_change_password"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vui lòng đổi mật khẩu trước khi sử dụng phân tích cảm xúc",
        )
    return user


def require_student_user(
    user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Sinh viên đã đăng nhập (JWT); không bắt buộc đổi mật khẩu — dùng cho đọc lịch sử."""
    if user.get("role") != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tài khoản sinh viên được xem lịch sử phản hồi",
        )
    return user


def require_student(
    user: Annotated[dict, Depends(require_password_changed)],
) -> dict:
    if user.get("role") != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tài khoản sinh viên được gửi phản hồi",
        )
    return user


def require_teacher(
    user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    if user.get("role") != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tài khoản giáo viên được xem dashboard phản hồi",
        )
    return user
