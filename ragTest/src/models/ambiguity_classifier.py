"""
BGE-m3-ko 기반 모호성 이진 분류기 모델 정의

Architecture:
  BGE-m3-ko encoder (XLM-RoBERTa-large, 1024-dim)
    → [CLS] token embedding
    → Dropout(0.1) → Linear(1024, 256) → ReLU → Dropout(0.1) → Linear(256, 1)
    → Sigmoid → 0~1 (모호성 확률)

입력: [CLS] query [SEP] category_description [SEP]
출력: 모호성 확률 (0=낮음, 1=높음)
"""

import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer


class AmbiguityClassifier(nn.Module):
    """(query, document) 쌍의 모호성을 판별하는 이진 분류기"""

    def __init__(self, model_name="upskyy/bge-m3-ko", hidden_dim=1024, dropout=0.1):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(model_name)
        self.hidden_dim = hidden_dim

        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 1),
        )

    def forward(self, input_ids, attention_mask, token_type_ids=None):
        """
        Args:
            input_ids: [batch, seq_len]
            attention_mask: [batch, seq_len]
            token_type_ids: [batch, seq_len] (optional)
        Returns:
            logits: [batch] - 모호성 logit (sigmoid 적용 전)
        """
        kwargs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        }
        if token_type_ids is not None:
            kwargs["token_type_ids"] = token_type_ids

        outputs = self.encoder(**kwargs)
        cls_embedding = outputs.last_hidden_state[:, 0, :]  # [CLS] token
        logit = self.classifier(cls_embedding).squeeze(-1)
        return logit

    def freeze_encoder(self):
        """Encoder 전체 동결 (Phase 1: head만 학습)"""
        for param in self.encoder.parameters():
            param.requires_grad = False

    def unfreeze_top_layers(self, num_layers=2):
        """Encoder 상위 N개 layer만 해동 (Phase 2: encoder 미세조정)"""
        # XLM-RoBERTa의 layer 구조
        encoder_layers = self.encoder.encoder.layer
        total_layers = len(encoder_layers)
        for i in range(total_layers - num_layers, total_layers):
            for param in encoder_layers[i].parameters():
                param.requires_grad = True

    def unfreeze_all(self):
        """모든 파라미터 해동"""
        for param in self.parameters():
            param.requires_grad = True


class AmbiguityDataset(torch.utils.data.Dataset):
    """모호성 분류기 학습 데이터셋"""

    def __init__(self, samples, tokenizer, max_length=256):
        """
        Args:
            samples: list of {"query": str, "document": str, "label": int}
            tokenizer: AutoTokenizer
            max_length: 최대 토큰 길이
        """
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        encoded = self.tokenizer(
            sample["query"],
            sample["document"],
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids": encoded["input_ids"].squeeze(0),
            "attention_mask": encoded["attention_mask"].squeeze(0),
            "label": torch.tensor(sample["label"], dtype=torch.float),
        }
