"""
Hồ sơ hiển thị header / UX sinh viên.
"""
from typing import Literal

from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    id: int
    username: str = Field(..., description="MSSV / mã đăng nhập")
    full_name: str
    role: Literal["student", "teacher"]
    class_id: int | None = None
    class_name: str | None = Field(None, description="Tên lớp hành chính")
    department: str | None = Field(None, description="Khoa quản lý lớp")
    must_change_password: bool
