"""
Pydantic schemas cho API sentiment.
"""
from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Văn bản cần phân tích cảm xúc")


class SentenceResult(BaseModel):
    text: str
    sentiment: str
    label_id: int
    probabilities: dict
    preprocessed_text: str


class PredictResponse(BaseModel):
    sentences: list[SentenceResult]


class PreprocessResponse(BaseModel):
    normalized: str = Field(..., description="Văn bản đã chuẩn hóa")
    words: list[str] = Field(..., description="Danh sách từ sau tách từ")
    preprocessed: str = Field(..., description="Văn bản sau pipeline đầy đủ")
