"""
train.py
학습 루프 — early stopping, 슬롯별 F1 로깅
"""

import json
import torch
import numpy as np
from pathlib import Path
from torch.utils.data import DataLoader
from torch.optim import AdamW
from transformers import get_linear_schedule_with_warmup
from sklearn.metrics import f1_score

from dataset import SlotFillingDataset, collate_fn
from model import SlotFillingModel, compute_loss


# ── 설정 ─────────────────────────────────────────────────────────────────────
CFG = {
    "model_name": "klue/roberta-base",
    "data_dir": "data",
    "output_dir": "checkpoints",
    "max_length": 128,
    "batch_size": 32,
    "lr": 2e-5,
    "weight_decay": 0.01,
    "epochs": 30,
    "warmup_ratio": 0.1,
    "dropout": 0.1,
    "label_smoothing": 0.1,
    "early_stopping_patience": 5,
    "seed": 42,
}


def set_seed(seed):
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def evaluate(model, loader, device, candidate_vocab):
    model.eval()
    all_status_preds, all_status_labels = [], []
    all_cat_preds, all_cat_labels = [], []
    total_loss = 0.0
    n_batches = 0

    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            token_type_ids = batch["token_type_ids"].to(device)
            status_labels = batch["status_labels"].to(device)
            cat_labels = batch["cat_labels"].to(device)
            span_start_labels = batch["span_start_labels"].to(device)
            span_end_labels = batch["span_end_labels"].to(device)
            is_categorical = batch["is_categorical"].to(device)
            is_span = batch["is_span"].to(device)
            is_active = batch["is_active"].to(device)

            s_logits, c_logits, ss_logits, se_logits = model(
                input_ids, attention_mask, token_type_ids
            )
            loss, _ = compute_loss(
                s_logits, c_logits, ss_logits, se_logits,
                status_labels, cat_labels, span_start_labels, span_end_labels,
                is_categorical, is_span, is_active,
            )
            total_loss += loss.item()
            n_batches += 1

            # Status predictions
            status_preds = s_logits.argmax(dim=-1).cpu().numpy()
            all_status_preds.extend(status_preds.tolist())
            all_status_labels.extend(status_labels.cpu().numpy().tolist())

            # Categorical predictions (ACTIVE + categorical 샘플만)
            cat_mask = (is_active * is_categorical).bool().cpu()
            if cat_mask.sum() > 0:
                c_preds = c_logits.argmax(dim=-1).cpu()
                all_cat_preds.extend(c_preds[cat_mask].numpy().tolist())
                all_cat_labels.extend(cat_labels.cpu()[cat_mask].numpy().tolist())

    avg_loss = total_loss / max(n_batches, 1)
    status_f1 = f1_score(all_status_labels, all_status_preds,
                         average="macro", zero_division=0)
    cat_acc = (np.array(all_cat_preds) == np.array(all_cat_labels)).mean() \
              if all_cat_preds else 0.0

    return avg_loss, status_f1, cat_acc


def train():
    set_seed(CFG["seed"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    Path(CFG["output_dir"]).mkdir(parents=True, exist_ok=True)

    # ── 데이터셋 ──────────────────────────────────────────────────────────
    train_ds = SlotFillingDataset(
        f"{CFG['data_dir']}/train.jsonl", CFG["model_name"], CFG["max_length"]
    )
    val_ds = SlotFillingDataset(
        f"{CFG['data_dir']}/val.jsonl", CFG["model_name"], CFG["max_length"]
    )
    # val_ds는 train_ds와 동일한 candidate_vocab을 공유해야 함
    val_ds.candidate_vocab = train_ds.candidate_vocab

    train_loader = DataLoader(train_ds, batch_size=CFG["batch_size"],
                              shuffle=True, collate_fn=collate_fn, num_workers=2)
    val_loader = DataLoader(val_ds, batch_size=CFG["batch_size"],
                            shuffle=False, collate_fn=collate_fn, num_workers=2)

    num_candidates = len(train_ds.candidate_vocab)
    print(f"Candidate vocab size: {num_candidates}")

    # vocab 저장
    with open(f"{CFG['output_dir']}/candidate_vocab.json", "w", encoding="utf-8") as f:
        json.dump(train_ds.candidate_vocab, f, ensure_ascii=False, indent=2)

    # ── 모델 ──────────────────────────────────────────────────────────────
    model = SlotFillingModel(
        model_name=CFG["model_name"],
        num_candidate_values=num_candidates,
        dropout=CFG["dropout"],
    ).to(device)

    # ── Optimizer & Scheduler ─────────────────────────────────────────────
    optimizer = AdamW(model.parameters(), lr=CFG["lr"],
                      weight_decay=CFG["weight_decay"])
    total_steps = len(train_loader) * CFG["epochs"]
    warmup_steps = int(total_steps * CFG["warmup_ratio"])
    scheduler = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    # ── 학습 루프 ─────────────────────────────────────────────────────────
    best_val_loss = float("inf")
    patience_counter = 0

    for epoch in range(1, CFG["epochs"] + 1):
        model.train()
        total_train_loss = 0.0
        loss_breakdown = {"status": 0.0, "categorical": 0.0, "span": 0.0}

        for step, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            token_type_ids = batch["token_type_ids"].to(device)
            status_labels = batch["status_labels"].to(device)
            cat_labels = batch["cat_labels"].to(device)
            span_start_labels = batch["span_start_labels"].to(device)
            span_end_labels = batch["span_end_labels"].to(device)
            is_categorical = batch["is_categorical"].to(device)
            is_span = batch["is_span"].to(device)
            is_active = batch["is_active"].to(device)

            optimizer.zero_grad()
            s_logits, c_logits, ss_logits, se_logits = model(
                input_ids, attention_mask, token_type_ids
            )
            loss, breakdown = compute_loss(
                s_logits, c_logits, ss_logits, se_logits,
                status_labels, cat_labels, span_start_labels, span_end_labels,
                is_categorical, is_span, is_active,
                label_smoothing=CFG["label_smoothing"],
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            total_train_loss += loss.item()
            for k in loss_breakdown:
                loss_breakdown[k] += breakdown[k]

        avg_train = total_train_loss / len(train_loader)
        for k in loss_breakdown:
            loss_breakdown[k] /= len(train_loader)

        # ── 검증 ──────────────────────────────────────────────────────────
        val_loss, status_f1, cat_acc = evaluate(
            model, val_loader, device, train_ds.candidate_vocab
        )

        print(f"Epoch {epoch:03d} | "
              f"Train: {avg_train:.4f} "
              f"(status={loss_breakdown['status']:.3f}, "
              f"cat={loss_breakdown['categorical']:.3f}, "
              f"span={loss_breakdown['span']:.3f}) | "
              f"Val: {val_loss:.4f} | "
              f"Status-F1: {status_f1:.4f} | "
              f"Cat-Acc: {cat_acc:.4f}")

        # ── Early Stopping & Checkpoint ───────────────────────────────────
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), f"{CFG['output_dir']}/best_model.pt")
            print(f"  ✓ Best model saved (val_loss={val_loss:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= CFG["early_stopping_patience"]:
                print(f"  Early stopping at epoch {epoch}")
                break

    print("학습 완료!")


if __name__ == "__main__":
    train()
