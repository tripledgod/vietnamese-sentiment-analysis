# Vietnamese Sentiment Analysis

Phân tích cảm xúc văn bản tiếng Việt sử dụng PhoBERT. Dataset: UIT-VSFC / VMTEB.

## Cấu trúc dự án

```
vietnamese-sentiment-analysis/
├── backend/           # REST API (FastAPI)
│   ├── app/
│   │   ├── api/       # Routes, endpoints
│   │   ├── core/      # Config, paths
│   │   ├── schemas/   # Pydantic models
│   │   └── services/  # Preprocessing, predictor
│   ├── requirements.txt
│   └── run.py
├── frontend/          # Giao diện demo
│   ├── index.html
│   └── README.md
├── data/              # Dữ liệu & model
│   ├── models/        # PhoBERT đã train
│   │   └── phobert_sentiment/
│   └── README.md
└── README.md
```

## Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python run.py
```

API chạy tại http://localhost:8001

### 2. Frontend

Mở `frontend/index.html` trong trình duyệt hoặc chạy static server:

```bash
cd frontend
python -m http.server 3000
# Truy cập http://localhost:3000
```

### 3. Model

Model đã có trong `data/models/phobert_sentiment/`. Nếu chưa có, tải từ [Google Drive](https://drive.google.com/drive/folders/10fTSurdv9Mu6nBmLc_elrWhfgOJzlUAh) và giải nén vào thư mục trên.

## API Endpoints

| Method | Endpoint       | Mô tả                                    |
|--------|----------------|------------------------------------------|
| POST   | `/predict`     | Phân tích cảm xúc                        |
| POST   | `/preprocess`  | Chỉ tiền xử lý                           |
| GET    | `/health`      | Kiểm tra trạng thái                      |

**Ví dụ:**

```bash
curl -X POST "http://localhost:8001/predict" \
  -H "Content-Type: application/json" \
  -d '{"text": "Sản phẩm rất tốt, giao hàng nhanh!"}'
```

## Pipeline

1. **Chuẩn hóa**: Unicode NFC, loại bỏ khoảng trắng thừa
2. **Tách từ**: Underthesea `word_tokenize`
3. **Dự đoán**: PhoBERT (RobertaForSequenceClassification, 3 lớp: negative, neutral, positive)

## Colab & Model

- [Colab notebook](https://colab.research.google.com/drive/1B1p755q0-Qf67USj8ku1W3hPCzHaUZu9)
- Model train từ: [another-symato/VMTEB-vietnamese_students_feedback_sentiment_word_segment](https://huggingface.co/datasets/another-symato/VMTEB-vietnamese_students_feedback_sentiment_word_segment)
