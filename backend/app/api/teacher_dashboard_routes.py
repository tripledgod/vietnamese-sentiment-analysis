"""
Thống kê & danh sách phản hồi cho trang Giáo viên (JWT role=teacher).
Đường dẫn /admin/... theo spec; xác thực Bearer, không dùng X-Admin-Key.
"""
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_teacher
from app.db import get_db
from app.schemas.teacher_dashboard import (
    AdminFeedbackRow,
    AdminFeedbacksListResponse,
    ClassesMetaResponse,
    ClassesStatsResponse,
    ClassMetaItem,
    ClassSentimentBreakdown,
    LABEL_VI,
    NegativeAlertItem,
    NegativeAlertsResponse,
    OverviewStatsResponse,
    SentimentShare,
)
from app.services.stats_repo import (
    VALID_LABELS,
    class_label_aggregates,
    count_all_feedbacks,
    count_by_label,
    count_students_with_feedback,
    list_all_classes,
    list_feedbacks_admin_filtered,
    list_negative_high_confidence,
)

router = APIRouter(tags=["teacher-dashboard"])


def _label_vi(label: str) -> str:
    return LABEL_VI.get(label, label)


@router.get("/admin/stats/overview", response_model=OverviewStatsResponse)
def admin_stats_overview(
    _: Annotated[dict, Depends(require_teacher)],
) -> OverviewStatsResponse:
    with get_db() as conn:
        n_students = count_students_with_feedback(conn)
        total_fb = count_all_feedbacks(conn)
        by_label = count_by_label(conn)

    pos_n = int(by_label.get("positive", 0))
    pos_rate = round((pos_n / total_fb * 100.0), 2) if total_fb else 0.0

    order = ["positive", "negative", "neutral"]
    shares: list[SentimentShare] = []
    for k in order:
        cnt = int(by_label.get(k, 0))
        pct = round((cnt / total_fb * 100.0), 2) if total_fb else 0.0
        shares.append(
            SentimentShare(label=k, label_vi=_label_vi(k), count=cnt, percent=pct)
        )

    other_sum = sum(c for lab, c in by_label.items() if lab not in VALID_LABELS)
    if other_sum:
        pct = round((other_sum / total_fb * 100.0), 2) if total_fb else 0.0
        shares.append(
            SentimentShare(
                label="other",
                label_vi="Khác",
                count=other_sum,
                percent=pct,
            )
        )

    return OverviewStatsResponse(
        total_students_participated=n_students,
        total_feedbacks=total_fb,
        positive_rate_percent=pos_rate,
        sentiment_distribution=shares,
    )


@router.get("/admin/meta/classes", response_model=ClassesMetaResponse)
def admin_meta_classes(
    _: Annotated[dict, Depends(require_teacher)],
) -> ClassesMetaResponse:
    """Danh sách lớp cho bộ lọc bảng phản hồi."""
    with get_db() as conn:
        rows = list_all_classes(conn)
    return ClassesMetaResponse(
        items=[
            ClassMetaItem(
                id=int(r["id"]),
                class_name=r["class_name"],
                department=r["department"] or "",
            )
            for r in rows
        ]
    )


@router.get("/admin/stats/classes", response_model=ClassesStatsResponse)
def admin_stats_classes(
    _: Annotated[dict, Depends(require_teacher)],
) -> ClassesStatsResponse:
    with get_db() as conn:
        raw = class_label_aggregates(conn)

    buckets: dict[str, dict] = defaultdict(
        lambda: {
            "class_id": None,
            "class_name": "",
            "department": "",
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "other": 0,
        }
    )

    for row in raw:
        cid = row["class_id"]
        key = f"id:{cid}" if cid is not None else "none"
        b = buckets[key]
        b["class_id"] = int(cid) if cid is not None else None
        b["class_name"] = row["class_name"] or "Chưa phân lớp"
        b["department"] = row["department"] or ""
        lab = str(row["label"])
        cnt = int(row["cnt"])
        if lab == "positive":
            b["positive"] += cnt
        elif lab == "negative":
            b["negative"] += cnt
        elif lab == "neutral":
            b["neutral"] += cnt
        else:
            b["other"] += cnt

    items: list[ClassSentimentBreakdown] = []
    for b in buckets.values():
        tot = b["positive"] + b["negative"] + b["neutral"] + b["other"]
        items.append(
            ClassSentimentBreakdown(
                class_id=b["class_id"],
                class_name=b["class_name"],
                department=b["department"],
                positive=b["positive"],
                negative=b["negative"],
                neutral=b["neutral"],
                other=b["other"],
                total=tot,
            )
        )

    items.sort(key=lambda x: (-x.negative, -x.total, x.class_name or ""))

    return ClassesStatsResponse(items=items)


@router.get("/admin/feedbacks/all", response_model=AdminFeedbacksListResponse)
def admin_feedbacks_all(
    _: Annotated[dict, Depends(require_teacher)],
    class_id: int | None = Query(None, description="Lọc theo lớp (users.class_id)"),
    label: str | None = Query(
        None,
        description="Lọc theo nhãn: positive | negative | neutral",
    ),
    q: str | None = Query(
        None,
        description="Tìm trong nội dung bình luận (không phân biệt hoa thường)",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AdminFeedbacksListResponse:
    if label is not None and label not in VALID_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="label phải là positive, negative hoặc neutral",
        )
    with get_db() as conn:
        total, rows = list_feedbacks_admin_filtered(
            conn,
            class_id=class_id,
            label=label,
            search_q=q,
            limit=limit,
            offset=offset,
        )

    items = [
        AdminFeedbackRow(
            id=r["id"],
            content=r["content"],
            label=str(r["label"]),
            label_vi=_label_vi(str(r["label"])),
            confidence=float(r["confidence"]),
            created_at=str(r["created_at"]),
            user_id=int(r["user_id"]),
            username=r["username"],
            student_full_name=r["student_full_name"] or "",
            class_id=int(r["class_id"]) if r["class_id"] is not None else None,
            class_name=r["class_name"],
            department=r["department"],
        )
        for r in rows
    ]
    return AdminFeedbacksListResponse(total=total, items=items)


@router.get("/admin/feedbacks/alerts", response_model=NegativeAlertsResponse)
def admin_feedbacks_alerts(
    _: Annotated[dict, Depends(require_teacher)],
    limit: int = Query(20, ge=1, le=50, description="Top N bình luận tiêu cực tin cậy cao"),
) -> NegativeAlertsResponse:
    with get_db() as conn:
        rows = list_negative_high_confidence(conn, limit=limit)

    items = [
        NegativeAlertItem(
            id=r["id"],
            content=r["content"],
            confidence=float(r["confidence"]),
            created_at=str(r["created_at"]),
            user_id=int(r["user_id"]),
            username=r["username"],
            student_full_name=r["student_full_name"] or "",
            class_id=int(r["class_id"]) if r["class_id"] is not None else None,
            class_name=r["class_name"],
            department=r["department"],
        )
        for r in rows
    ]
    return NegativeAlertsResponse(items=items)
