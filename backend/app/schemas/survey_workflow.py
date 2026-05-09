"""API khảo sát theo kỳ / môn / lớp."""
from pydantic import BaseModel, Field


class SemesterOut(BaseModel):
    id: int
    name: str


class SubjectOut(BaseModel):
    id: int
    subject_name: str
    subject_code: str


class ClassMetaOut(BaseModel):
    id: int
    class_name: str
    department: str


class SurveyConfigRowOut(BaseModel):
    subject_id: int
    subject_name: str
    subject_code: str
    survey_config_id: int | None
    is_active: bool


class SurveyActivateRequest(BaseModel):
    class_id: int = Field(..., ge=1)
    semester_id: int = Field(..., ge=1)
    active_subject_ids: list[int] = Field(
        ...,
        description="Danh sách id môn được mở khảo sát (các môn khác trong kỳ sẽ tắt)",
    )


class StudentSurveyOfferingOut(BaseModel):
    survey_config_id: int
    subject_name: str
    subject_code: str
    semester_name: str
    semester_id: int
