"""
model.py
SlotFillingModel — KLUE-RoBERTa + 4 heads
"""

import torch
import torch.nn as nn
from transformers import AutoModel


class SlotFillingModel(nn.Module):
    def __init__(self, model_name: str = "klue/roberta-base",
                 num_candidate_values: int = 100,
                 dropout: float = 0.1):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(model_name)
        hidden = self.encoder.config.hidden_size  # 768

        # ── Head 1: Slot Status (NONE=0 / ACTIVE=1) ────────────────────────
        self.status_head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden, 2),
        )

        # ── Head 2: Categorical Value Scorer ──────────────────────────────
        # CLS 벡터 → 후보값 수만큼 logit
        self.categorical_head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden, num_candidate_values),
        )

        # ── Head 3 & 4: Span Start / End ──────────────────────────────────
        self.span_start_head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden, 1),
        )
        self.span_end_head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden, 1),
        )

    def forward(self, input_ids, attention_mask, token_type_ids=None):
        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
        )
        sequence_output = outputs.last_hidden_state  # (B, seq_len, H)
        cls_output = sequence_output[:, 0, :]        # (B, H)

        status_logits = self.status_head(cls_output)           # (B, 2)
        cat_logits = self.categorical_head(cls_output)         # (B, num_cands)
        span_start_logits = self.span_start_head(sequence_output).squeeze(-1)  # (B, seq_len)
        span_end_logits = self.span_end_head(sequence_output).squeeze(-1)      # (B, seq_len)

        return status_logits, cat_logits, span_start_logits, span_end_logits


def compute_loss(status_logits, cat_logits, span_start_logits, span_end_logits,
                 status_labels, cat_labels, span_start_labels, span_end_labels,
                 is_categorical, is_span, is_active,
                 label_smoothing: float = 0.1):
    """
    Loss 계산 with masking
    - status loss: 모든 샘플
    - categorical value loss: ACTIVE + is_categorical 샘플만
    - span loss: ACTIVE + is_span 샘플만
    """
    ce = nn.CrossEntropyLoss(label_smoothing=label_smoothing, reduction="none")

    # ── Status Loss ────────────────────────────────────────────────────────
    status_loss = ce(status_logits, status_labels).mean()

    # ── Categorical Value Loss ─────────────────────────────────────────────
    cat_mask = (is_active * is_categorical).bool()
    if cat_mask.sum() > 0:
        cat_loss = ce(cat_logits[cat_mask], cat_labels[cat_mask]).mean()
    else:
        cat_loss = torch.tensor(0.0, device=status_logits.device)

    # ── Span Loss ──────────────────────────────────────────────────────────
    span_mask = (is_active * is_span).bool()
    if span_mask.sum() > 0:
        start_loss = ce(span_start_logits[span_mask], span_start_labels[span_mask]).mean()
        end_loss = ce(span_end_logits[span_mask], span_end_labels[span_mask]).mean()
        span_loss = (start_loss + end_loss) / 2
    else:
        span_loss = torch.tensor(0.0, device=status_logits.device)

    total = status_loss + cat_loss + span_loss
    return total, {"status": status_loss.item(),
                   "categorical": cat_loss.item(),
                   "span": span_loss.item()}
