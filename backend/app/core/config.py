"""
Cấu hình ứng dụng, đường dẫn model, JWT và CSDL người dùng.
"""
import os
from pathlib import Path

# Thư mục gốc dự án (4 cấp lên từ backend/app/core/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = DATA_DIR / "models"
MODEL_PATH = MODELS_DIR / "phobert_sentiment"

DATABASE_PATH = DATA_DIR / "users.db"

# Mặc định >= 32 byte cho HS256 (đổi bằng biến môi trường khi triển khai).
JWT_SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY",
    "vietnamese-sentiment-dev-secret-key-32b!",
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", str(60 * 24 * 7)))

# Mật khẩu trước khi người dùng đổi (seed + import Excel — không đọc mật khẩu từ file).
DEFAULT_INITIAL_PASSWORD = os.environ.get("DEFAULT_INITIAL_PASSWORD", "Huce@123")

# Khóa import Excel / nạp master (header: X-Admin-Key). Để trống = tắt các endpoint đó.
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "").strip()
