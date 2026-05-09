"""
API routes cho sentiment analysis.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_predictor_for_inference, require_model_access
from app.schemas import PreprocessResponse, PredictRequest, PredictResponse
from app.services import (
    normalize_text,
    preprocess,
    segment_words,
    split_by_newlines,
)
from app.services.sentiment_pipeline import build_predict_response

router = APIRouter(tags=["sentiment"])


@router.get("/health")
def health():
    import os

    from app.core import predictor_holder as ph

    pred = get_predictor_for_inference()
    return {
        "status": "ok",
        "model_loaded": pred is not None,
        "pid": os.getpid(),
        "predictor_holder_file": getattr(ph, "__file__", ""),
    }


@router.post("/predict", response_model=PredictResponse)
def predict(
    body: PredictRequest,
    _user: Annotated[dict, Depends(require_model_access)],
):
    """Không có \\n: 1 lần PhoBERT. Có \\n: tách dòng, N lần PhoBERT."""
    try:
        return build_predict_response(body.text, get_predictor_for_inference())
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/preprocess", response_model=PreprocessResponse)
def preprocess_only(
    request: PredictRequest,
    _user: Annotated[dict, Depends(require_model_access)],
):
    """Chỉ tiền xử lý (chuẩn hóa + tách từ)."""
    normalized = normalize_text(request.text)
    words = segment_words(normalized)
    preprocessed = " ".join(words) if words else ""
    return PreprocessResponse(
        normalized=normalized,
        words=words,
        preprocessed=preprocessed,
    )
