# Data

Thư mục chứa dữ liệu và artifact của dự án.

## Cấu trúc

```
data/
├── models/           # Model ML đã train
│   └── phobert_sentiment/   # PhoBERT sentiment (3 lớp)
├── datasets/         # Dataset gốc (tùy chọn)
└── README.md
```

## Model

- **phobert_sentiment**: PhoBERT fine-tuned cho phân tích cảm xúc (negative, neutral, positive)
- Format: Hugging Face Transformers (config, tokenizer, safetensors)

## Thêm model mới

Đặt model vào `data/models/<tên_model>/` và cập nhật `backend/app/core/config.py`.
