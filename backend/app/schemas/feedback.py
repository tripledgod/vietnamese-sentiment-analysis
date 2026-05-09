"""
Schema API phản hồi (Feedbacks) và dashboard giáo viên.
"""
from pydantic import BaseModel, Field, model_validator

from app.schemas.sentiment import SentenceResult


class SurveyAnswerItem(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)


class FeedbackSubmitRequest(BaseModel):
    content: str | None = Field(
        default=None,
        description="Khảo sát tự do; để trống nếu gửi theo môn (survey_config_id + answers).",
    )
    survey_config_id: int | None = None
    answers: list[SurveyAnswerItem] | None = None

    @model_validator(mode="after")
    def content_or_survey(self) -> "FeedbackSubmitRequest":
        if self.survey_config_id is not None:
            if not self.answers or len(self.answers) < 1:
                raise ValueError("Khi có survey_config_id cần gửi answers (ít nhất 1 câu)")
            return self
        if self.content is None or not str(self.content).strip():
            raise ValueError("Cần content hoặc cặp survey_config_id + answers")
        return self


class FeedbackSubmitResponse(BaseModel):
    id: int
    label: str
    confidence: float
    message: str = "Đã lưu phản hồi và kết quả PhoBERT"
    sentences: list[SentenceResult] = Field(
        default_factory=list,
        description="Chi tiết PhoBERT theo từng đoạn (giống /predict)",
    )


class FeedbackDashboardItem(BaseModel):
    id: int
    content: str
    label: str
    confidence: float
    created_at: str
    user_id: int
    username: str
    student_full_name: str
    student_class_id: int | None = None
    class_name: str | None = None
    department: str | None = None


class FeedbackDashboardResponse(BaseModel):
    total: int
    items: list[FeedbackDashboardItem]


class FeedbackHistoryRound(BaseModel):
    """Một lượt đánh giá = một bản ghi feedbacks (theo id / thời điểm gửi)."""

    round_id: int = Field(..., description="Trùng id bảng feedbacks (định danh lượt gửi)")
    created_at: str
    content: str = Field(..., description="Toàn bộ nội dung gốc đã gửi")
    survey_config_id: int | None = None
    subject_name: str | None = None
    semester_name: str | None = None
    stored_label: str = Field(..., description="Nhãn đoạn đầu đã lưu trong DB khi gửi")
    stored_confidence: float = Field(..., description="Độ tin cậy đoạn đầu đã lưu")
    sentences: list[SentenceResult] = Field(
        default_factory=list,
        description="Các câu/đoạn sau khi chạy lại pipeline PhoBERT (cùng logic lúc gửi)",
    )


class FeedbackMyHistoryResponse(BaseModel):
    total: int
    rounds: list[FeedbackHistoryRound]
