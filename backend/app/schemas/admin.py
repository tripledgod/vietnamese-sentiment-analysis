"""
Schema API quản trị (lớp học, import, …).
"""
from pydantic import BaseModel, Field


class AdminClassCreate(BaseModel):
    class_name: str = Field(..., min_length=1, description="Tên lớp hành chính")
    department: str = Field(
        default="",
        description="Khoa / đơn vị quản lý (có thể để trống)",
    )


class AdminClassResponse(BaseModel):
    id: int
    class_name: str
    department: str
