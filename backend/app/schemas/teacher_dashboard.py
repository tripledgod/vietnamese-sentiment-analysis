"""
Schema API thống kê & bảng phản hồi cho trang Giáo viên.
"""
from pydantic import BaseModel, Field


LABEL_VI = {
    "positive": "Tích cực",
    "negative": "Tiêu cực",
    "neutral": "Trung tính",
}


class SentimentShare(BaseModel):
    label: str = Field(..., description="Mã nhãn PhoBERT: positive / negative / neutral")
    label_vi: str
    count: int
    percent: float = Field(..., description="Tỷ lệ % trên tổng bình luận (0–100)")


class OverviewStatsResponse(BaseModel):
    total_students_participated: int = Field(
        ...,
        description="Số sinh viên có ít nhất một bản ghi feedbacks",
    )
    total_feedbacks: int = Field(..., description="Tổng số bình luận (hàng feedbacks)")
    positive_rate_percent: float = Field(
        ...,
        description="Tỷ lệ % nhãn tích cực trên tổng bình luận (hài lòng)",
    )
    sentiment_distribution: list[SentimentShare]


class ClassMetaItem(BaseModel):
    id: int
    class_name: str
    department: str


class ClassesMetaResponse(BaseModel):
    items: list[ClassMetaItem]


class ClassSentimentBreakdown(BaseModel):
    class_id: int | None = Field(None, description="NULL nếu sinh viên chưa gán lớp")
    class_name: str
    department: str
    positive: int = 0
    negative: int = 0
    neutral: int = 0
    other: int = 0
    total: int = 0


class ClassesStatsResponse(BaseModel):
    items: list[ClassSentimentBreakdown]


class AdminFeedbackRow(BaseModel):
    id: int
    content: str
    label: str
    label_vi: str
    confidence: float
    created_at: str
    user_id: int
    username: str
    student_full_name: str
    class_id: int | None = None
    class_name: str | None = None
    department: str | None = None


class AdminFeedbacksListResponse(BaseModel):
    total: int
    items: list[AdminFeedbackRow]


class NegativeAlertItem(BaseModel):
    id: int
    content: str
    confidence: float
    created_at: str
    user_id: int
    username: str
    student_full_name: str
    class_id: int | None = None
    class_name: str | None = None
    department: str | None = None


class NegativeAlertsResponse(BaseModel):
    items: list[NegativeAlertItem]
