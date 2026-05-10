"""
Chạy PhoBERT trên văn bản (tách dòng giống /predict).
"""
import re
import unicodedata

from app.schemas.sentiment import PredictResponse, SentenceResult
from app.services import preprocess, split_by_newlines
from app.services.predictor import SentimentPredictor

# Khớp frontend/js/student-survey-subject.js (không đổi text nếu không đồng bộ cả hai phía).
SURVEY_TEACHER_NAME_QUESTION = "Tên giảng viên phụ trách môn học"
SURVEY_OPTIONAL_COMMENT_QUESTION = (
    'Bạn có góp ý thêm nào khác không? (Nếu không, ghi "Không")'
)


def _fold_vi_lower(s: str) -> str:
    s = unicodedata.normalize("NFD", re.sub(r"\s+", " ", (s or "").strip()).casefold())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _strip_surrounding_quotes(s: str) -> str:
    t = s.strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'“”‘’":
        return t[1:-1].strip()
    return t


def is_effectively_no_extra_comment(answer: str) -> bool:
    """Trả lời kiểu «Không» (thường/hoa, thừa khoảng trắng) → không đưa vào PhoBERT."""
    a = _strip_surrounding_quotes(str(answer or ""))
    a = re.sub(r"\s+", " ", a).strip()
    if not a:
        return True
    folded = _fold_vi_lower(a)
    return folded in {"khong", "ko"}


def should_skip_survey_block_for_sentiment(question: str, answer: str) -> bool:
    q = (question or "").strip()
    if q == SURVEY_TEACHER_NAME_QUESTION:
        return True
    if q == SURVEY_OPTIONAL_COMMENT_QUESTION and is_effectively_no_extra_comment(answer):
        return True
    return False


def survey_answers_text_for_model(answers: list) -> str:
    """Ghép câu trả lời gửi PhoBERT (bỏ tên GV, bỏ «Không» ở câu góp ý thêm)."""
    parts: list[str] = []
    for item in answers:
        q = str(getattr(item, "question", "")).strip()
        a = str(getattr(item, "answer", "")).strip()
        if not a or should_skip_survey_block_for_sentiment(q, a):
            continue
        parts.append(a)
    return "\n".join(parts)


def text_for_survey_sentiment(stored_content: str) -> str:
    """
    Nội dung khảo sát theo môn lưu trong DB: mỗi khối «câu hỏi\\nCâu trả lời», các khối cách nhau \\n\\n.
    Chỉ ghép các câu trả lời (mỗi dòng một ý) để PhoBERT không phân loại nhầm phần câu hỏi.
    """
    if not stored_content or not isinstance(stored_content, str):
        return ""
    text = stored_content.replace("\r\n", "\n").replace("\r", "\n")
    parts = text.split("\n\n")
    answers: list[str] = []
    for raw in parts:
        block = raw.strip()
        if not block:
            continue
        if "\n" not in block:
            answers.append(block)
            continue
        _q, a = block.split("\n", 1)
        a_stripped = a.strip()
        if a_stripped and not should_skip_survey_block_for_sentiment(_q.strip(), a_stripped):
            answers.append(a_stripped)
    return "\n".join(answers) if answers else text.strip()


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


def build_predict_response_for_feedback(
    *,
    content: str,
    survey_config_id: int | None,
    predictor: SentimentPredictor | None,
) -> PredictResponse:
    """Khảo sát theo môn: chỉ chạy model trên các câu trả lời; phản hồi tự do: toàn bộ content."""
    if survey_config_id is not None:
        t = text_for_survey_sentiment(content)
        if not t.strip():
            t = " "
        return build_predict_response(t, predictor)
    return build_predict_response(content, predictor)


def first_block_label_and_confidence(pr: PredictResponse) -> tuple[str, float]:
    first = pr.sentences[0]
    probs = first.probabilities or {}
    conf = float(max(probs.values())) if probs else 0.0
    return str(first.sentiment), conf
