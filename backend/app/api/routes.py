"""
API routes cho sentiment analysis.
"""
from fastapi import APIRouter, HTTPException

from app.schemas import PreprocessResponse, PredictRequest, PredictResponse, SentenceResult
from app.services import (
    SentimentPredictor,
    normalize_text,
    preprocess,
    segment_words,
    split_by_newlines,
)

router = APIRouter(tags=["sentiment"])

# Inject predictor via dependency hoặc global (set trong main)
predictor: SentimentPredictor | None = None


def set_predictor(p: SentimentPredictor) -> None:
    global predictor
    predictor = p


@router.get("/health")
def health():
    return {"status": "ok", "model_loaded": predictor is not None}


@router.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    """Không có \\n: 1 lần PhoBERT. Có \\n: tách dòng, N lần PhoBERT."""
    if predictor is None:
        raise HTTPException(status_code=503, detail="Model chưa được tải")

    blocks = split_by_newlines(request.text) or [request.text.strip() or " "]
    sentences = []
    for block in blocks:
        preprocessed = preprocess(block)
        r = predictor.predict(preprocessed, return_probabilities=True)
        sentences.append(
            SentenceResult(
                text=block,
                sentiment=r["sentiment"],
                label_id=r["label_id"],
                probabilities=r["probabilities"],
                preprocessed_text=preprocessed,
            )
        )
    return PredictResponse(sentences=sentences)


@router.post("/preprocess", response_model=PreprocessResponse)
def preprocess_only(request: PredictRequest):
    """Chỉ tiền xử lý (chuẩn hóa + tách từ)."""
    normalized = normalize_text(request.text)
    words = segment_words(normalized)
    preprocessed = " ".join(words) if words else ""
    return PreprocessResponse(
        normalized=normalized,
        words=words,
        preprocessed=preprocessed,
    )
