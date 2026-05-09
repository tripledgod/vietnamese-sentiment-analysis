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
- Format: Hugging Face Transformers (config, tokenizer, **file trọng số** như `model.safetensors` hoặc `pytorch_model.bin`)
- Trên Git, `data/models/` và `*.safetensors` thường **không** được commit (`.gitignore`). Sau khi clone, cần **copy nguyên thư mục model đầy đủ** (kể cả trọng số) vào `data/models/phobert_sentiment/` — chỉ có tokenizer/config mà thiếu weights thì backend sẽ lỗi khi load.

## Thêm model mới

Đặt model vào `data/models/<tên_model>/` và cập nhật `backend/app/core/config.py`.
