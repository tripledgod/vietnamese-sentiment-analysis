# Backend API

REST API phân tích cảm xúc tiếng Việt - FastAPI + PhoBERT.

## Chạy

```bash
pip install -r requirements.txt
python run.py
```
Hoặc:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

**Lưu ý:** Chạy từ thư mục `backend/`. Model được load từ `../data/models/phobert_sentiment/`.

