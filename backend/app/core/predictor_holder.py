"""
Singleton process-local: chỉ main.py (lifespan) ghi, deps chỉ đọc.

Tránh đặt biến trong router modules (dễ trùng import với uvicorn reload)
và không phụ thuộc request.app.state.
"""
from __future__ import annotations

from app.services.predictor import SentimentPredictor

_held: SentimentPredictor | None = None


def set_held_predictor(p: SentimentPredictor | None) -> None:
    global _held
    _held = p


def get_held_predictor() -> SentimentPredictor | None:
    return _held
