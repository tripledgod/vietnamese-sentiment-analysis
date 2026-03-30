"""
Cấu hình ứng dụng, đường dẫn model.
"""
from pathlib import Path

# Thư mục gốc dự án (4 cấp lên từ backend/app/core/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = DATA_DIR / "models"
MODEL_PATH = MODELS_DIR / "phobert_sentiment"
