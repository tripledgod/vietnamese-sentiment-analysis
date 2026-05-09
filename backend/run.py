"""
Entry point chạy backend API.
Chạy từ thư mục backend: python run.py

Mặc định reload=False. Bật tự reload khi dev: `UVICORN_RELOAD=1 python run.py`
(hoặc `set UVICORN_RELOAD=1` trên Windows CMD rồi chạy). Trên Windows, reload đôi khi
gây lệch model — nếu lỗi, tắt reload và khởi động lại tay.
Cần reload tay không dùng biến: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

Cổng mặc định 8000. Nếu Errno 10048 (port đang bị chiếm): tắt server cũ hoặc
  set PORT=8002 && python run.py
"""
import os

import uvicorn

if __name__ == "__main__":
    _port = int(os.environ.get("PORT", "8000"))
    _reload = os.environ.get("UVICORN_RELOAD", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=_port,
        reload=_reload,
    )
