"""
Schema đăng nhập JWT và đổi mật khẩu.
"""
from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Username: MSSV (theo ERD). Cổng đăng nhập phải khớp role trong CSDL."""

    username: str = Field(..., min_length=1, description="Mã số sinh viên / mã đăng nhập")
    password: str = Field(..., min_length=1)
    portal: Literal["student", "teacher"] = Field(
        ...,
        description="student = cổng SV, teacher = cổng giảng viên",
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool
    role: Literal["student", "teacher"]
    username: str
    full_name: str
    class_id: int | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, description="Mật khẩu mới tối thiểu 8 ký tự")


class UserMeResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: Literal["student", "teacher"]
    class_id: int | None = None
    must_change_password: bool
