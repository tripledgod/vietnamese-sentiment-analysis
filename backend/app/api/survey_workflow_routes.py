"""
Luồng khảo sát theo lớp / kỳ / môn (giảng viên cấu hình, sinh viên điền form).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_student_user, require_teacher
from app.db import get_db
from app.schemas.survey_workflow import (
    ClassMetaOut,
    SemesterOut,
    StudentSurveyOfferingOut,
    SubjectOut,
    SurveyActivateRequest,
    SurveyConfigRowOut,
)
from app.services import survey_repo

router = APIRouter(tags=["survey-workflow"])


@router.get("/teacher/survey/semesters", response_model=list[SemesterOut])
def teacher_list_semesters(_: Annotated[dict, Depends(require_teacher)]) -> list[SemesterOut]:
    with get_db() as conn:
        rows = survey_repo.list_semesters(conn)
    return [SemesterOut(**r) for r in rows]


@router.get(
    "/teacher/survey/semesters/{semester_id}/subjects",
    response_model=list[SubjectOut],
)
def teacher_subjects_for_semester(
    semester_id: int,
    _: Annotated[dict, Depends(require_teacher)],
) -> list[SubjectOut]:
    with get_db() as conn:
        ex = conn.execute(
            "SELECT 1 FROM semesters WHERE id = ?", (semester_id,)
        ).fetchone()
        if not ex:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Kỳ học không tồn tại")
        rows = survey_repo.list_subjects_for_semester(conn, semester_id)
    return [SubjectOut(**r) for r in rows]


@router.get("/teacher/survey/classes", response_model=list[ClassMetaOut])
def teacher_list_classes(_: Annotated[dict, Depends(require_teacher)]) -> list[ClassMetaOut]:
    with get_db() as conn:
        rows = survey_repo.list_classes(conn)
    return [ClassMetaOut(**r) for r in rows]


@router.get(
    "/teacher/survey/configs",
    response_model=list[SurveyConfigRowOut],
)
def teacher_list_configs(
    class_id: int,
    semester_id: int,
    _: Annotated[dict, Depends(require_teacher)],
) -> list[SurveyConfigRowOut]:
    with get_db() as conn:
        ex = conn.execute("SELECT 1 FROM classes WHERE id = ?", (class_id,)).fetchone()
        if not ex:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lớp không tồn tại")
        ex2 = conn.execute(
            "SELECT 1 FROM semesters WHERE id = ?", (semester_id,)
        ).fetchone()
        if not ex2:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Kỳ học không tồn tại")
        rows = survey_repo.list_configs_for_class_semester(
            conn, class_id=class_id, semester_id=semester_id
        )
    return [SurveyConfigRowOut(**r) for r in rows]


@router.post("/teacher/survey/activate", status_code=status.HTTP_200_OK)
def teacher_activate_surveys(
    body: SurveyActivateRequest,
    _: Annotated[dict, Depends(require_teacher)],
) -> dict:
    with get_db() as conn:
        ex = conn.execute(
            "SELECT 1 FROM classes WHERE id = ?", (body.class_id,)
        ).fetchone()
        if not ex:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lớp không tồn tại")
        ex2 = conn.execute(
            "SELECT 1 FROM semesters WHERE id = ?", (body.semester_id,)
        ).fetchone()
        if not ex2:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Kỳ học không tồn tại")
        try:
            survey_repo.upsert_survey_activation(
                conn,
                class_id=body.class_id,
                semester_id=body.semester_id,
                active_subject_ids=set(body.active_subject_ids),
            )
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return {"ok": True, "message": "Đã cập nhật môn mở khảo sát cho lớp và kỳ đã chọn"}


@router.get(
    "/student/survey/offerings",
    response_model=list[StudentSurveyOfferingOut],
)
def student_survey_offerings(
    user: Annotated[dict, Depends(require_student_user)],
) -> list[StudentSurveyOfferingOut]:
    cid = user.get("class_id")
    if cid is None:
        return []
    uid = int(user["id"])
    with get_db() as conn:
        rows = survey_repo.list_active_offerings_for_student(
            conn, class_id=int(cid), user_id=uid
        )
    return [StudentSurveyOfferingOut(**r) for r in rows]
