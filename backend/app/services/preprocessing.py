"""
Tiền xử lý văn bản tiếng Việt cho phân tích cảm xúc.
- Chuẩn hóa: unicode, khoảng trắng
- Tách từ: Underthesea
"""
import re
import unicodedata
from typing import List

from underthesea import word_tokenize


def normalize_text(text: str) -> str:
    """
    Chuẩn hóa văn bản tiếng Việt.
    - Chuẩn hóa unicode (NFC)
    - Loại bỏ khoảng trắng thừa
    """
    if not text or not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def segment_words(text: str) -> List[str]:
    """Tách từ tiếng Việt sử dụng Underthesea."""
    if not text or not isinstance(text, str):
        return []
    tokens = word_tokenize(text)
    return tokens if isinstance(tokens, list) else [str(tokens)]


def split_by_newlines(text: str) -> list[str]:
    """Tách theo \\n: không có \\n → 1 block; có \\n → N blocks."""
    if not text or not isinstance(text, str):
        return []
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "\n" not in text:
        stripped = re.sub(r"\s+", " ", text).strip()
        return [stripped] if stripped else []
    return [re.sub(r"\s+", " ", line).strip() for line in text.split("\n") if line.strip()]


def preprocess(text: str) -> str:
    """Pipeline: Chuẩn hóa -> Tách từ -> Ghép (phù hợp PhoBERT)."""
    normalized = normalize_text(text)
    if not normalized:
        return ""
    words = segment_words(normalized)
    return " ".join(words) if words else ""
