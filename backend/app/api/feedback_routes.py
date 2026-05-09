"""
Sinh viên gửi phản hồi (lưu Feedbacks); giáo viên xem dashboard.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_predictor_for_inference, require_student, require_student_user, require_teacher
from app.db import get_db
from app.schemas.feedback import (
    FeedbackDashboardItem,
    FeedbackDashboardResponse,
    FeedbackHistoryRound,
    FeedbackMyHistoryResponse,
    FeedbackSubmitRequest,
    FeedbackSubmitResponse,
)
from app.services import survey_repo
from app.services.feedbacks_repo import (
    count_feedbacks,
    count_feedbacks_by_user,
    insert_feedback,
    list_feedbacks_by_user,
    list_feedbacks_for_dashboard,
)
from app.services.sentiment_pipeline import build_predict_response, first_block_label_and_confidence

router = APIRouter(tags=["feedbacks"])


@router.post("/feedbacks", response_model=FeedbackSubmitResponse)
def submit_feedback(
    body: FeedbackSubmitRequest,
    user: Annotated[dict, Depends(require_student)],
) -> FeedbackSubmitResponse:
    survey_cfg: int | None = None
    if body.survey_config_id is not None:
        user_cid = user.get("class_id")
        if user_cid is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tài khoản chưa được gán lớp — không thể gửi khảo sát theo môn",
            )
        with get_db() as conn:
            ok = survey_repo.assert_config_active_for_class(
                conn,
                config_id=int(body.survey_config_id),
                student_class_id=int(user_cid),
            )
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Khảo sát này không mở cho lớp của bạn hoặc đã tắt",
            )
        survey_cfg = int(body.survey_config_id)
        text_for_model = "\n\n".join(
            f"{a.question.strip()}\n{a.answer.strip()}" for a in (body.answers or [])
        )
    else:
        text_for_model = (body.content or "").strip()

    try:
        pr = build_predict_response(text_for_model, get_predictor_for_inference())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    label, confidence = first_block_label_and_confidence(pr)
    with get_db() as conn:
        fid = insert_feedback(
            conn,
            user_id=int(user["id"]),
            content=text_for_model,
            label=label,
            confidence=confidence,
            survey_config_id=survey_cfg,
        )
    return FeedbackSubmitResponse(
        id=fid,
        label=label,
        confidence=confidence,
        sentences=pr.sentences,
    )


@router.get("/feedbacks/my-history", response_model=FeedbackMyHistoryResponse)
def my_feedback_history(
    user: Annotated[dict, Depends(require_student_user)],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> FeedbackMyHistoryResponse:
    """
    Lịch sử phản hồi của sinh viên đang đăng nhập.
    Mỗi phần tử `rounds` = một lượt gửi (theo `id` bảng feedbacks / thời gian).
    `sentences` được tái tạo bằng PhoBERT trên `content` đã lưu (cùng pipeline với lúc gửi).
    """
    uid = int(user["id"])
    with get_db() as conn:
        total = count_feedbacks_by_user(conn, uid)
        rows = list_feedbacks_by_user(conn, user_id=uid, limit=limit, offset=offset)

    rounds: list[FeedbackHistoryRound] = []
    for r in rows:
        sentences = []
        try:
            pr = build_predict_response(r["content"], get_predictor_for_inference())
            sentences = list(pr.sentences)
        except ValueError:
            sentences = []
        scid = r["survey_config_id"] if r["survey_config_id"] is not None else None
        rounds.append(
            FeedbackHistoryRound(
                round_id=int(r["id"]),
                created_at=str(r["created_at"]),
                content=r["content"],
                survey_config_id=int(scid) if scid is not None else None,
                subject_name=r["subject_name"] if r["subject_name"] else None,
                semester_name=r["semester_name"] if r["semester_name"] else None,
                stored_label=str(r["label"]),
                stored_confidence=float(r["confidence"]),
                sentences=sentences,
            )
        )

    return FeedbackMyHistoryResponse(total=total, rounds=rounds)


@router.get("/teacher/dashboard/feedbacks", response_model=FeedbackDashboardResponse)
def teacher_dashboard_feedbacks(
    user: Annotated[dict, Depends(require_teacher)],
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Lọc theo độ tin cậy tối thiểu"),
    class_id: int | None = Query(None, description="Lọc theo lớp (users.class_id)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> FeedbackDashboardResponse:
    _ = user
    with get_db() as conn:
        total = count_feedbacks(conn, min_confidence=min_confidence, class_id=class_id)
        rows = list_feedbacks_for_dashboard(
            conn,
            min_confidence=min_confidence,
            class_id=class_id,
            limit=limit,
            offset=offset,
        )
    items = [
        FeedbackDashboardItem(
            id=r["id"],
            content=r["content"],
            label=r["label"],
            confidence=float(r["confidence"]),
            created_at=str(r["created_at"]),
            user_id=int(r["user_id"]),
            username=r["username"],
            student_full_name=r["student_full_name"] or "",
            student_class_id=int(r["student_class_id"])
            if r["student_class_id"] is not None
            else None,
            class_name=r["class_name"],
            department=r["department"],
        )
        for r in rows
    ]
    return FeedbackDashboardResponse(total=total, items=items)
