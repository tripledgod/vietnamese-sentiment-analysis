"""
Đăng nhập JWT, /me, đổi mật khẩu.
"""
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import get_db
from app.api.deps import get_current_user
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse, UserMeResponse
from app.services.auth_service import create_access_token, hash_password, verify_password
from app.services.users import find_by_username, get_user_by_id, set_password

router = APIRouter(tags=["auth"])


def _normalize_login_username(raw: str) -> str:
    """Chuẩn hóa MSSV: khoảng trắng, ký tự full-width (NFKC)."""
    return unicodedata.normalize("NFKC", (raw or "").strip())


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    password = body.password.strip()
    if not password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai tên đăng nhập hoặc mật khẩu",
        )
    username = _normalize_login_username(body.username)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai tên đăng nhập hoặc mật khẩu",
        )
    with get_db() as conn:
        row = find_by_username(conn, username)
        ph = row["password_hash"] if row is not None else None
        if row is None or not ph or not verify_password(password, ph):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sai tên đăng nhập hoặc mật khẩu",
            )
        if row["role"] != body.portal:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản không thuộc cổng đăng nhập này",
            )
        # Giáo viên: tài khoản tạo sẵn, không ép đổi mật khẩu lần đầu.
        must_change = (
            bool(row["must_change_password"]) if row["role"] == "student" else False
        )
        token = create_access_token(
            user_id=int(row["id"]),
            username=row["username"],
            role=row["role"],
            must_change_password=must_change,
        )
        cid = row["class_id"]
        return TokenResponse(
            access_token=token,
            must_change_password=must_change,
            role=row["role"],
            username=row["username"],
            full_name=row["full_name"] or "",
            class_id=int(cid) if cid is not None else None,
        )


@router.get("/auth/me", response_model=UserMeResponse)
def me(user: dict = Depends(get_current_user)) -> UserMeResponse:
    return UserMeResponse(
        id=user["id"],
        username=user["username"],
        full_name=user["full_name"],
        role=user["role"],
        class_id=user.get("class_id"),
        must_change_password=user["must_change_password"],
    )


@router.post("/auth/change-password")
def change_password(
    body: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    with get_db() as conn:
        row = get_user_by_id(conn, user["id"])
        if row is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Người dùng không tồn tại")
        if not verify_password(body.old_password, row["password_hash"]):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Mật khẩu hiện tại không đúng",
            )
        set_password(
            conn,
            user["id"],
            hash_password(body.new_password),
            clear_must_change=True,
        )
    return {"ok": True, "message": "Đã cập nhật mật khẩu"}
