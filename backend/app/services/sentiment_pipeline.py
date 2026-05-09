"""
Chạy PhoBERT trên văn bản (tách dòng giống /predict).
"""
from app.schemas.sentiment import PredictResponse, SentenceResult
from app.services import preprocess, split_by_newlines
from app.services.predictor import SentimentPredictor


def build_predict_response(text: str, predictor: SentimentPredictor | None) -> PredictResponse:
    if predictor is None:
        raise ValueError("Model chưa được tải")
    blocks = split_by_newlines(text) or [text.strip() or " "]
    sentences: list[SentenceResult] = []
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


def first_block_label_and_confidence(pr: PredictResponse) -> tuple[str, float]:
    first = pr.sentences[0]
    probs = first.probabilities or {}
    conf = float(max(probs.values())) if probs else 0.0
    return str(first.sentiment), conf
