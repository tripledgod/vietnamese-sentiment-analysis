"""
REST API phân tích cảm xúc tiếng Việt - FastAPI.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# backend/.env — trước mọi import đọc os.environ (config, v.v.)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.core import MODEL_PATH
from app.core.config import DEFAULT_INITIAL_PASSWORD
from app.core.predictor_holder import set_held_predictor
from app.db import init_db
from app.services import SentimentPredictor
from app.services.auth_service import hash_password
from app.services.users import seed_demo_users_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo CSDL người dùng và load model."""
    init_db()
    seed_demo_users_if_empty(hash_password(DEFAULT_INITIAL_PASSWORD))
    try:
        pred = SentimentPredictor(MODEL_PATH)
        set_held_predictor(pred)
        app.state.predictor = pred
        from app.core import predictor_holder as _ph_verify

        if _ph_verify.get_held_predictor() is not pred:
            raise RuntimeError(
                "predictor_holder không đồng bộ sau khi load model (hai bản module app?)."
            )
    except FileNotFoundError as e:
        raise RuntimeError(
            f"Không tìm thấy model tại {MODEL_PATH}. "
            "Đảm bảo data/models/phobert_sentiment/ tồn tại."
        ) from e
    yield
    set_held_predictor(None)
    app.state.predictor = None


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
