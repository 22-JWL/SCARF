"""
evaluate_test.py
test.jsonl로 상세 평가 + 틀린 샘플 CSV 저장
"""

import csv
import json
import torch
import numpy as np
from pathlib import Path
from torch.utils.data import DataLoader
from transformers import AutoTokenizer
from sklearn.metrics import f1_score, classification_report
from collections import defaultdict

from dataset import SlotFillingDataset, collate_fn
from model import SlotFillingModel

CFG = {
    "model_name":      "klue/roberta-base",
    "checkpoint_dir":  "checkpoints", #"checkpoints_finetune", 
    "test_path":       "eval_data/test.jsonl",# "data/test.jsonl", #
    "max_length":      128,
    "batch_size":      32,
    "show_errors":     True,
    "max_errors_shown": 20,
    "error_csv_path":  "errors.csv",
}


def token_f1(pred_tokens: set, gold_tokens: set) -> float:
    if not pred_tokens and not gold_tokens:
        return 1.0
    if not pred_tokens or not gold_tokens:
        return 0.0
    common = pred_tokens & gold_tokens
    p = len(common) / len(pred_tokens)
    r = len(common) / len(gold_tokens)
    return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def decode_span(input_ids, start, end, tokenizer):
    ids = input_ids[start:end + 1].tolist()
    return tokenizer.decode(ids, skip_special_tokens=True).strip()


def save_errors_csv(cat_errors: list, span_errors: list, path: str):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "타입", "슬롯명", "발화", "정답", "예측", "정답토큰범위", "예측토큰범위"
        ])
        writer.writeheader()
        for e in cat_errors:
            writer.writerow({
                "타입": "categorical", "슬롯명": e["slot_name"],
                "발화": e["utterance"], "정답": e["gold"], "예측": e["pred"],
                "정답토큰범위": "", "예측토큰범위": "",
            })
        for e in span_errors:
            writer.writerow({
                "타입": "span", "슬롯명": e["slot_name"],
                "발화": e["utterance"], "정답": e["gold"], "예측": e["pred"],
                "정답토큰범위": e["gold_token_range"], "예측토큰범위": e["pred_token_range"],
            })
    print(f"  → 오류 CSV 저장: {path}  (categorical {len(cat_errors)}건, span {len(span_errors)}건)")


def evaluate_test():
    # device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device("cpu")
    print(f"Device: {device}")

    with open(f"{CFG['checkpoint_dir']}/candidate_vocab.json", encoding="utf-8") as f:
        candidate_vocab = json.load(f)
    id2cand = {v: k for k, v in candidate_vocab.items()}
    tokenizer = AutoTokenizer.from_pretrained(CFG["model_name"])

    test_ds = SlotFillingDataset(CFG["test_path"], CFG["model_name"], CFG["max_length"])
    test_ds.candidate_vocab = candidate_vocab
    test_loader = DataLoader(test_ds, batch_size=CFG["batch_size"],
                             shuffle=False, collate_fn=collate_fn)

    model = SlotFillingModel(
        model_name=CFG["model_name"],
        num_candidate_values=len(candidate_vocab),
    ).to(device)
    model.load_state_dict(
        torch.load(f"{CFG['checkpoint_dir']}/best_model.pt", map_location=device)
    )
    model.eval()

    all_status_preds, all_status_labels = [], []
    slot_cat_results  = defaultdict(lambda: {"correct": 0, "total": 0, "errors": []})
    slot_span_results = defaultdict(lambda: {"em": [], "f1": [], "errors": []})
    all_cat_errors, all_span_errors = [], []

    with torch.no_grad():
        for batch in test_loader:
            input_ids      = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            token_type_ids = batch["token_type_ids"].to(device)
            status_labels     = batch["status_labels"]
            cat_labels        = batch["cat_labels"]
            span_start_labels = batch["span_start_labels"]
            span_end_labels   = batch["span_end_labels"]
            is_categorical = batch["is_categorical"]
            is_span        = batch["is_span"]
            is_active      = batch["is_active"]

            s_logits, c_logits, ss_logits, se_logits = model(
                input_ids, attention_mask, token_type_ids
            )
            status_preds     = s_logits.argmax(dim=-1).cpu()
            span_start_preds = ss_logits.argmax(dim=-1).cpu()
            span_end_preds   = se_logits.argmax(dim=-1).cpu()

            for i in range(input_ids.shape[0]):
                slot_name  = batch["slot_names"][i]
                utterance  = batch["utterances"][i]
                gold_value = batch["values"][i]
                gold_status = status_labels[i].item()

                all_status_preds.append(status_preds[i].item())
                all_status_labels.append(gold_status)

                if is_categorical[i].item() == 1 and is_active[i].item() == 1:
                    candidates = batch["candidates"][i]
                    if candidates:
                        cand_indices = [candidate_vocab.get(c, 1) for c in candidates]
                        best = c_logits[i, cand_indices].argmax().item()
                        pred_value = candidates[best]
                    else:
                        pred_value = id2cand.get(c_logits[i].argmax().item(), "<unknown>")

                    slot_cat_results[slot_name]["total"] += 1
                    if pred_value == gold_value:
                        slot_cat_results[slot_name]["correct"] += 1
                    else:
                        err = {"slot_name": slot_name, "utterance": utterance,
                               "gold": gold_value, "pred": pred_value}
                        slot_cat_results[slot_name]["errors"].append(err)
                        all_cat_errors.append(err)

                if is_span[i].item() == 1 and is_active[i].item() == 1:
                    pred_s = span_start_preds[i].item()
                    pred_e = span_end_preds[i].item()
                    gold_s = span_start_labels[i].item()
                    gold_e = span_end_labels[i].item()
                    if pred_e < pred_s:
                        pred_e = pred_s

                    pred_text = decode_span(input_ids[i].cpu(), pred_s, pred_e, tokenizer)

                    # ── 여기서 공백 제거
                    pred_text = tokenizer.convert_tokens_to_string(
                        tokenizer.convert_ids_to_tokens(tokenizer(pred_text, add_special_tokens=False)["input_ids"])
                    ).replace(" ", "")

                    gold_text = gold_value  # 원본 텍스트
                    em = int(pred_text == gold_text)
                    f1 = token_f1(set(pred_text.split()), set(gold_text.split()))

                    slot_span_results[slot_name]["em"].append(em)
                    slot_span_results[slot_name]["f1"].append(f1)

                    if not em:
                        err = {
                            "slot_name": slot_name, "utterance": utterance,
                            "gold": gold_text, "pred": pred_text,
                            "gold_token_range": f"{gold_s}~{gold_e}",
                            "pred_token_range": f"{pred_s}~{pred_e}",
                        }
                        slot_span_results[slot_name]["errors"].append(err)
                        all_span_errors.append(err)

    # ── 출력 ──────────────────────────────────────────────────────────────
    if slot_name == "tab_name":
        print(f"candidates: {candidates}")
        print(f"cand_indices: {cand_indices}")
        print(f"logits: {c_logits[i, cand_indices].tolist()}")
        print(f"best idx: {best}")

    print("\n" + "=" * 65)
    print("  TEST EVALUATION RESULTS")
    print("=" * 65)

    status_f1 = f1_score(all_status_labels, all_status_preds, average="macro", zero_division=0)
    print(f"\n[Status] Macro-F1: {status_f1:.4f}")
    print(classification_report(all_status_labels, all_status_preds,
                                target_names=["NONE", "ACTIVE"], zero_division=0))

    print("-" * 65)
    print("[Categorical Slots] Accuracy by slot")
    print(f"  {'슬롯명':<35} {'정확도':>8}  {'맞춤/전체':>10}")
    print(f"  {'-'*35} {'-'*8}  {'-'*10}")
    tc, ta = 0, 0
    for slot, res in sorted(slot_cat_results.items()):
        acc = res["correct"] / res["total"] if res["total"] > 0 else 0.0
        print(f"  {slot:<35} {acc:>8.4f}  {res['correct']:>5}/{res['total']:<5}")
        tc += res["correct"]; ta += res["total"]
    print(f"  {'[전체]':<35} {tc/ta if ta else 0:>8.4f}  {tc:>5}/{ta:<5}")

    print("-" * 65)
    print("[Span Slots] Exact Match & F1 by slot")
    print(f"  {'슬롯명':<35} {'EM':>8}  {'F1':>8}  {'샘플수':>6}")
    print(f"  {'-'*35} {'-'*8}  {'-'*8}  {'-'*6}")
    all_em, all_f1 = [], []
    for slot, res in sorted(slot_span_results.items()):
        em = np.mean(res["em"]) if res["em"] else 0.0
        f1 = np.mean(res["f1"]) if res["f1"] else 0.0
        print(f"  {slot:<35} {em:>8.4f}  {f1:>8.4f}  {len(res['em']):>6}")
        all_em.extend(res["em"]); all_f1.extend(res["f1"])
    if all_em:
        print(f"  {'[전체]':<35} {np.mean(all_em):>8.4f}  {np.mean(all_f1):>8.4f}  {len(all_em):>6}")

    if CFG["show_errors"]:
        print("\n" + "=" * 65)
        print("  CATEGORICAL ERRORS (샘플)")
        print("=" * 65)
        for err in all_cat_errors[:CFG["max_errors_shown"]]:
            print(f"  슬롯: {err['slot_name']}")
            print(f"  발화: {err['utterance']}")
            print(f"  정답: {err['gold']}  예측: {err['pred']}")
            print()

        print("=" * 65)
        print("  SPAN ERRORS (샘플)")
        print("=" * 65)
        for err in all_span_errors[:CFG["max_errors_shown"]]:
            print(f"  슬롯: {err['slot_name']}")
            print(f"  발화: {err['utterance']}")
            print(f"  정답: '{err['gold']}'  예측: '{err['pred']}'")
            print(f"  토큰범위 정답:{err['gold_token_range']}  예측:{err['pred_token_range']}")
            print()

    print("=" * 65)
    save_errors_csv(all_cat_errors, all_span_errors, CFG["error_csv_path"])


if __name__ == "__main__":
    evaluate_test()