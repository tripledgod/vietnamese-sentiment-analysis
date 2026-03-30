"""
REST API phân tích cảm xúc tiếng Việt - FastAPI.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.api.routes import set_predictor
from app.core import MODEL_PATH
from app.services import SentimentPredictor


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model khi khởi động."""
    try:
        pred = SentimentPredictor(MODEL_PATH)
        set_predictor(pred)
    except FileNotFoundError as e:
        raise RuntimeError(
            f"Không tìm thấy model tại {MODEL_PATH}. "
            "Đảm bảo data/models/phobert_sentiment/ tồn tại."
        ) from e
    yield
    set_predictor(None)


app = FastAPI(
    title="Vietnamese Sentiment Analysis API",
    description="API phân tích cảm xúc văn bản tiếng Việt sử dụng PhoBERT",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "message": "Vietnamese Sentiment Analysis API",
        "docs": "/docs",
        "health": "/health",
        "predict": "/predict",
    }
