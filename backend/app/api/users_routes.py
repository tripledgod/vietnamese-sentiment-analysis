"""
Hồ sơ người dùng (header / UX).
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.db import get_db
from app.schemas.user_profile import UserProfileResponse
from app.services.stats_repo import get_user_profile_row

router = APIRouter(tags=["users"])


@router.get("/users/me", response_model=UserProfileResponse)
def users_me(user: dict = Depends(get_current_user)) -> UserProfileResponse:
    """Tên, MSSV, lớp & khoa (join classes) cho lời chào trên header."""
    with get_db() as conn:
        row = get_user_profile_row(conn, int(user["id"]))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng")

    cid = row["class_id"]
    must = bool(row["must_change_password"])
    if row["role"] == "teacher":
        must = False
    return UserProfileResponse(
        id=int(row["id"]),
        username=row["username"],
        full_name=row["full_name"] or "",
        role=row["role"],
        class_id=int(cid) if cid is not None else None,
        class_name=row["class_name"],
        department=row["department"],
        must_change_password=must,
    )
