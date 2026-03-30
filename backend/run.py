"""
Entry point chạy backend API.
Chạy từ thư mục backend: python run.py
Hoặc: uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
