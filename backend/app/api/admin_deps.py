"""
Xác thực khóa quản trị (header X-Admin-Key).
"""
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import ADMIN_API_KEY


def require_admin_api_key(
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
) -> None:
    if not ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chưa cấu hình ADMIN_API_KEY trên server",
        )
    if not x_admin_key or x_admin_key.strip() != ADMIN_API_KEY:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Khóa quản trị không hợp lệ",
        )
