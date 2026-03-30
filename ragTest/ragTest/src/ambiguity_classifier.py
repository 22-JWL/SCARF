"""
모호성 분류기 추론 모듈

사용법:
    from ambiguity_classifier import classify_ambiguity

    result = classify_ambiguity("임계값 올려", "검사할 대상이 패키지 표면에서...")
    # {"is_ambiguous": False, "ambiguity_score": 0.12, "confidence": "low_ambiguity"}
"""

import json
import os
import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer

# ─── 모델 정의 (학습 모듈과 동일 구조) ───

class _AmbiguityClassifierModel(nn.Module):
    def __init__(self, model_name, hidden_dim=1024, dropout=0.1):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(model_name)
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 1),
        )

    def forward(self, input_ids, attention_mask):
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls_embedding = outputs.last_hidden_state[:, 0, :]
        logit = self.classifier(cls_embedding).squeeze(-1)
        return logit


# ─── 싱글톤 로더 ───

_instance = None


def load_ambiguity_classifier(
    checkpoint_dir=None,
    device="cpu",
):
    """
    모호성 분류기를 로드합니다 (싱글톤).

    Args:
        checkpoint_dir: 체크포인트 디렉토리 경로.
            기본값: src/checkpoints/bge_m3_ko_ambiguity_classifier/
        device: "cpu" 또는 "cuda"

    Returns:
        dict with keys: model, tokenizer, config, device
    """
    global _instance
    if _instance is not None:
        return _instance

    if checkpoint_dir is None:
        checkpoint_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "checkpoints",
            "bge_m3_ko_ambiguity_classifier_v2",
        )

    # config 로드
    config_path = os.path.join(checkpoint_dir, "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    model_name = config["model_name"]
    max_length = config.get("max_length", 256)
    threshold = config.get("threshold", 0.5)

    # 토크나이저
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # 모델 로드
    model = _AmbiguityClassifierModel(
        model_name=model_name,
        hidden_dim=config.get("hidden_dim", 1024),
        dropout=config.get("dropout", 0.1),
    )

    model_path = os.path.join(checkpoint_dir, "model.pt")
    state_dict = torch.load(model_path, map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    _instance = {
        "model": model,
        "tokenizer": tokenizer,
        "config": config,
        "max_length": max_length,
        "threshold": threshold,
        "device": device,
    }
    print(f"모호성 분류기 로드 완료 (threshold={threshold})")
    return _instance


def classify_ambiguity(query, document_text, threshold=None):
    """
    (query, document) 쌍의 모호성을 판별합니다.

    Args:
        query: 사용자 질의 (str)
        document_text: Retriever가 찾은 카테고리 설명 (str)
        threshold: 판별 임계값 (None이면 config 기본값 사용)

    Returns:
        dict:
            is_ambiguous (bool): True이면 모호성 높음
            ambiguity_score (float): 0~1 모호성 확률
            confidence (str): "high_ambiguity" / "mid_ambiguity" / "low_ambiguity"
    """
    comp = load_ambiguity_classifier()
    model = comp["model"]
    tokenizer = comp["tokenizer"]
    max_length = comp["max_length"]
    device = comp["device"]

    if threshold is None:
        threshold = comp["threshold"]

    inputs = tokenizer(
        query,
        document_text,
        max_length=max_length,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    ).to(device)

    with torch.no_grad():
        logit = model(inputs["input_ids"], inputs["attention_mask"])
        prob = torch.sigmoid(logit).item()

    return {
        "is_ambiguous": prob >= threshold,
        "ambiguity_score": round(prob, 4),
        "confidence": (
            "high_ambiguity" if prob >= 0.8
            else "mid_ambiguity" if prob >= threshold
            else "low_ambiguity"
        ),
    }
