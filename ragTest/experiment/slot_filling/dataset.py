"""
dataset.py
SlotFillingDataset — KLUE-RoBERTa 기반
입력: utterance + slot_description 결합
출력: status / categorical value / span start&end
"""

import json
import torch
from torch.utils.data import Dataset
from transformers import AutoTokenizer


class SlotFillingDataset(Dataset):
    def __init__(self, jsonl_path: str, tokenizer_name: str = "klue/roberta-base",
                 max_length: int = 128):
        self.samples = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.samples.append(json.loads(line))

        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        self.max_length = max_length

        # 슬롯 후보 값 → index 매핑 (categorical용)
        # 전체 유니크 candidates를 모아서 공통 vocabulary 구성
        self.candidate_vocab = self._build_candidate_vocab()

    def _build_candidate_vocab(self):
        """모든 categorical 후보값을 하나의 vocab으로 통합"""
        vocab = {"<none>": 0, "<unknown>": 1}
        for s in self.samples:
            for cand in s.get("candidates", []):
                if cand not in vocab:
                    vocab[cand] = len(vocab)
        return vocab

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        utterance = s["utterance"]
        slot_desc = s["slot_description"]

        # ── 토크나이즈: [CLS] utterance [SEP] slot_description [SEP] ──────
        enc = self.tokenizer(
            utterance,
            slot_desc,
            max_length=self.max_length,
            truncation=True,
            padding="max_length",
            return_offsets_mapping=True,
            return_tensors="pt",
        )

        input_ids = enc["input_ids"].squeeze(0)
        attention_mask = enc["attention_mask"].squeeze(0)
        token_type_ids = enc.get("token_type_ids", torch.zeros_like(input_ids)).squeeze(0)
        offset_mapping = enc["offset_mapping"].squeeze(0)  # (seq_len, 2)

        # ── Status 레이블 ─────────────────────────────────────────────────
        status_map = {"NONE": 0, "ACTIVE": 1}
        status_label = status_map.get(s["status"], 0)

        # ── Categorical value 레이블 ──────────────────────────────────────
        cat_label = 0  # default: <none>
        if s["slot_type"] == "categorical" and s["status"] == "ACTIVE":
            cat_label = self.candidate_vocab.get(s["value"],
                        self.candidate_vocab.get("<unknown>", 1))

        # ── Span 레이블 ───────────────────────────────────────────────────
        # 원본 char offset → token index 변환
        span_start_label = 0
        span_end_label = 0
        if s["slot_type"] == "span" and s["status"] == "ACTIVE":
            char_start = s["span_start"]
            char_end = s["span_end"]
            if char_start >= 0 and char_end >= 0:
                span_start_label, span_end_label = self._char_to_token(
                    offset_mapping, char_start, char_end, utterance
                )

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": token_type_ids,
            "slot_type": s["slot_type"],           # "categorical" or "span"
            "status_label": torch.tensor(status_label, dtype=torch.long),
            "cat_label": torch.tensor(cat_label, dtype=torch.long),
            "span_start_label": torch.tensor(span_start_label, dtype=torch.long),
            "span_end_label": torch.tensor(span_end_label, dtype=torch.long),
            # 추론 시 사용
            "candidates": s.get("candidates", []),
            "value": s.get("value", ""),
            "slot_name": s["slot_name"],
            "utterance": utterance,
        }

    def _char_to_token(self, offset_mapping, char_start, char_end, utterance):
        """
        char offset → token index 변환
        utterance는 sentence A이므로 [CLS] 다음부터 시작
        """
        seq_len = offset_mapping.shape[0]
        tok_start, tok_end = 0, 0

        for i in range(seq_len):
            tok_char_start, tok_char_end = offset_mapping[i].tolist()
            if tok_char_start == 0 and tok_char_end == 0:
                continue  # special token
            if tok_char_start <= char_start < tok_char_end:
                tok_start = i
            if tok_char_start < char_end <= tok_char_end:
                tok_end = i
                break

        # 범위 클리핑
        tok_start = min(tok_start, seq_len - 1)
        tok_end = min(tok_end, seq_len - 1)
        if tok_end < tok_start:
            tok_end = tok_start

        return tok_start, tok_end


def collate_fn(batch):
    """DataLoader용 collate — slot_type별로 마스크 생성"""
    input_ids = torch.stack([b["input_ids"] for b in batch])
    attention_mask = torch.stack([b["attention_mask"] for b in batch])
    token_type_ids = torch.stack([b["token_type_ids"] for b in batch])
    status_labels = torch.stack([b["status_label"] for b in batch])
    cat_labels = torch.stack([b["cat_label"] for b in batch])
    span_start_labels = torch.stack([b["span_start_label"] for b in batch])
    span_end_labels = torch.stack([b["span_end_label"] for b in batch])

    # 슬롯 타입별 마스크
    is_categorical = torch.tensor([1 if b["slot_type"] == "categorical" else 0 for b in batch])
    is_span = torch.tensor([1 if b["slot_type"] == "span" else 0 for b in batch])
    is_active = torch.tensor([1 if b["status_label"].item() == 1 else 0 for b in batch])

    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "token_type_ids": token_type_ids,
        "status_labels": status_labels,
        "cat_labels": cat_labels,
        "span_start_labels": span_start_labels,
        "span_end_labels": span_end_labels,
        "is_categorical": is_categorical,
        "is_span": is_span,
        "is_active": is_active,
        # 메타 (추론용)
        "candidates": [b["candidates"] for b in batch],
        "values": [b["value"] for b in batch],
        "slot_names": [b["slot_name"] for b in batch],
        "utterances": [b["utterance"] for b in batch],
    }
