"""
Tích hợp mô hình PhoBERT để dự đoán cảm xúc.
"""
from pathlib import Path
from typing import Dict, Optional

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

DEFAULT_LABEL_MAP = {
    "LABEL_0": "negative",
    "LABEL_1": "neutral",
    "LABEL_2": "positive",
}


class SentimentPredictor:
    """Wrapper cho mô hình PhoBERT sentiment."""

    def __init__(self, model_path: str | Path):
        self.model_path = Path(model_path)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer: Optional[AutoTokenizer] = None
        self.model = None
        self.id2label: Dict[str, str] = DEFAULT_LABEL_MAP
        self._load_model()

    def _load_model(self) -> None:
        path = self.model_path.resolve()
        if not path.exists():
            raise FileNotFoundError(f"Model path không tồn tại: {path}")

        self.tokenizer = AutoTokenizer.from_pretrained(str(path))
        self.model = AutoModelForSequenceClassification.from_pretrained(str(path))
        self.model.to(self.device)
        self.model.eval()

        if hasattr(self.model.config, "id2label") and self.model.config.id2label:
            raw = self.model.config.id2label
            self.id2label = {
                str(k): DEFAULT_LABEL_MAP.get(str(v), str(v))
                for k, v in raw.items()
            }

    def predict(self, text: str, return_probabilities: bool = True) -> Dict:
        """Dự đoán cảm xúc cho văn bản."""
        if not text or not text.strip():
            return {
                "sentiment": "neutral",
                "label_id": 1,
                "probabilities": {"negative": 0.33, "neutral": 0.34, "positive": 0.33},
            }

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=256,
            padding=True,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)

        logits = outputs.logits[0]
        probs = torch.softmax(logits, dim=-1).cpu().numpy()
        pred_id = int(logits.argmax().item())
        sentiment = self.id2label.get(str(pred_id), f"LABEL_{pred_id}")

        result: Dict = {"sentiment": sentiment, "label_id": pred_id}
        if return_probabilities:
            result["probabilities"] = {
                self.id2label.get(str(i), f"LABEL_{i}"): float(probs[i])
                for i in range(len(probs))
            }
        return result
