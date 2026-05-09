"""
Nạp danh sách người dùng từ Excel; tạo lớp (Admin, khóa X-Admin-Key).
"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.admin_deps import require_admin_api_key
from app.db import get_db
from app.schemas.admin import AdminClassCreate, AdminClassResponse
from app.services.classes_repo import ensure_class
from app.services.excel_import import import_master_excel_bytes, import_users_from_excel_bytes

router = APIRouter(tags=["admin"])


@router.post("/admin/classes", response_model=AdminClassResponse)
def create_class(
    body: AdminClassCreate,
    _: Annotated[None, Depends(require_admin_api_key)],
) -> AdminClassResponse:
    """Tạo lớp nếu chưa tồn tại (khớp class_name + department); dùng trước khi import Excel."""
    cn = body.class_name.strip()
    dep = (body.department or "").strip()
    with get_db() as conn:
        cid = ensure_class(conn, class_name=cn, department=dep)
    return AdminClassResponse(id=cid, class_name=cn, department=dep)


@router.post("/admin/users/import-excel")
async def import_excel(
    _: Annotated[None, Depends(require_admin_api_key)],
    file: UploadFile = File(..., description="File .xlsx"),
) -> dict:
    name = (file.filename or "").lower()
    if not name.endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Chỉ hỗ trợ file Excel .xlsx / .xlsm",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File rỗng")

    result = import_users_from_excel_bytes(raw)
    return {"ok": len(result.get("errors", [])) == 0, **result}


@router.post("/admin/import-master-excel")
async def import_master_excel(
    _: Annotated[None, Depends(require_admin_api_key)],
    file: UploadFile = File(..., description="File .xlsx 3 sheet: Subjects, Classes, Users"),
) -> dict:
    """
    Nạp danh mục môn + lớp + sinh viên theo một file Excel.
    Hệ thống nhận diện từng sheet theo **tiêu đề cột** (tên sheet đặt tùy ý).
    """
    name = (file.filename or "").lower()
    if not name.endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Chỉ hỗ trợ file Excel .xlsx / .xlsm",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File rỗng")

    return import_master_excel_bytes(raw)


@router.get("/admin/import-master-excel")
def import_master_excel_info() -> dict[str, Any]:
    """
    Kiểm tra nhanh: mở trình duyệt GET URL này — nếu 404 thì server đang chạy bản code cũ
    (cần tắt và chạy lại `python run.py`), hoặc sai cổng / sai host.
    Upload thật vẫn là POST + X-Admin-Key + multipart field `file`.
    """
    return {
        "ok": True,
        "upload_method": "POST",
        "path": "/admin/import-master-excel",
        "headers": {"required_for_post": "X-Admin-Key"},
        "body": "multipart/form-data, field name: file",
        "file_types": [".xlsx", ".xlsm"],
        "note": "Định dạng đúng là .xlsx (không phải .xlxs).",
    }
