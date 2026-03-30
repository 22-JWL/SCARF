"""
evaluate_e2e_classifier.py

BGE-m3-ko Ambiguity Classifier 평가 스크립트
- classify_ambiguity()에 들어가는 input(text, action_doc)과 output(score)을 CSV에 기록
- retrieve_action() top-k 후보 중 action_doc에 포함된 것을 표시

[CSV 컬럼]
  ── classifier input ──
  text              : 사용자 입력
  action_doc        : classify_ambiguity()에 전달된 document ("\n" 구분)
  doc_count         : action_doc에 포함된 API description 개수

  ── classifier output ──
  ambiguity_score   : sigmoid 확률 (0~1)
  confidence        : high_ambiguity / mid_ambiguity / low_ambiguity
  threshold         : 판정 기준 threshold

  ── 정답 / 판정 ──
  gt_classifier     : 정답 (0=모호, 1=명확)
  pred_classifier   : 예측 (0=모호, 1=명확)
  classifier_correct: 일치 여부

  ── retrieve_action top-k ──
  topN_api_name     : API 이름
  topN_description  : description (action.json)
  topN_useCase      : useCase (action.json)
  topN_score        : Chroma distance (낮을수록 유사)
  topN_in_doc       : action_doc에 포함 여부 (1/0)
"""

import sys
import csv, time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag_pipeline import (
    run_pipeline,
    classify_ambiguity,
    _make_action_document,
)

INTENT_MAP = {
    "calibration":    "calibration_control",
    "change_mode":    "change_operation",
    "history_set":    "history_control",
    "setting_Preset": "recipe_management",
    "chat_clear":     "chat_clear",
    "close_windows":  "close_windows",
    "no_function":    "no_function",
}

TEST_CSV   = str(PROJECT_ROOT / "test_queries_labeled_url.csv")
OUTPUT_DIR = PROJECT_ROOT / "eval_results"
OUTPUT_DIR.mkdir(exist_ok=True)
TIMESTAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
RESULT_CSV = OUTPUT_DIR / f"eval_classifier_{TIMESTAMP}.csv"

TOP_K = 5

# ── CSV 컬럼 정의 ─────────────────────────────────────────────────────────────
FIELDNAMES = [
    # 기본
    "id", "text",
    # Stage1
    "gt_intent", "pred_intent", "intent_correct",
    # classifier input
    "action_doc", "doc_count",
    # classifier output
    "ambiguity_score", "confidence", "threshold",
    # 판정
    "gt_classifier", "pred_classifier", "classifier_correct",
]
# top-k 후보 (api_name, description, useCase, score, in_doc)
for k in range(TOP_K):
    FIELDNAMES += [
        f"top{k+1}_api_name",
        f"top{k+1}_description",
        f"top{k+1}_useCase",
        f"top{k+1}_score",
        f"top{k+1}_in_doc",
    ]


def _count_docs(action_doc: str) -> int:
    """action_doc 내 description 개수"""
    if not action_doc:
        return 0
    return action_doc.count("\n") + 1


def _in_action_doc(candidate: dict, action_doc: str) -> bool:
    """해당 후보의 description이 action_doc에 포함되어 있는지"""
    desc = candidate.get("description", "")
    return bool(desc and desc in action_doc)


def evaluate_classifier():
    rows = list(csv.DictReader(open(TEST_CSV, encoding="utf-8-sig")))
    results = []

    total = len(rows)
    intent_correct = 0
    clf_correct = 0

    print(f"BGE-m3-ko Ambiguity Classifier 평가 — 총 {total}개")
    print(f"{'='*90}")
    print(f"  {'id':>3}  I C  {'gt':>2} {'pred':>4} {'score':>7} {'docs':>4}  text")
    print(f"  {'-'*84}")

    for i, row in enumerate(rows):
        rid  = row["id"]
        text = row["text"].strip()
        gt_intent = INTENT_MAP.get(row["subCategory"].strip(), row["subCategory"].strip())
        gt_clf    = int(row["index_Classifier"])  # 0=모호, 1=명확

        # ── Stage 1: classify_command ────────────────────────────────────────
        sub_category, mode = run_pipeline.classify_command(text)

        action_candidates = []
        action_doc  = ""
        score       = 0.0
        confidence  = ""
        threshold   = 0.0

        if mode == "reject":
            pred_intent = "no_function"
            pred_clf    = 1
            confidence  = "rejected"
        else:
            intent = sub_category[0] if isinstance(sub_category, list) else sub_category
            pred_intent = INTENT_MAP.get(intent, intent)

            # ── Stage 2a: retrieve_action ────────────────────────────────────
            action_candidates = run_pipeline.retrieve_action(sub_category, text, k=TOP_K)

            # ── Stage 2b: classify_ambiguity ─────────────────────────────────
            if action_candidates:
                action_doc = _make_action_document(action_candidates)
                ambiguity  = classify_ambiguity(text, action_doc)
            else:
                ambiguity = run_pipeline.check_ambiguity(text, sub_category)

            pred_clf   = 0 if ambiguity["is_ambiguous"] else 1
            score      = round(ambiguity.get("ambiguity_score", 0.0), 4)
            confidence = ambiguity.get("confidence", "")
            # threshold는 싱글톤에서 가져옴
            from rag_pipeline import classify_ambiguity as _ca
            from ragTest.src.ambiguity_classifier import _instance
            if _instance:
                threshold = _instance.get("threshold", 0.0)

        doc_count = _count_docs(action_doc)

        i_ok = (pred_intent == gt_intent)
        c_ok = (pred_clf == gt_clf)
        intent_correct += int(i_ok)
        clf_correct    += int(c_ok)

        print(f"  {rid:>3}  {'O' if i_ok else 'X'} {'O' if c_ok else 'X'}  "
              f"{gt_clf:>2} {pred_clf:>4} {score:>7.4f} {doc_count:>4}  {text[:45]}")

        # ── row 조립 ─────────────────────────────────────────────────────────
        row_data = {
            "id": rid, "text": text,
            "gt_intent": gt_intent, "pred_intent": pred_intent,
            "intent_correct": int(i_ok),
            "action_doc": action_doc,
            "doc_count": doc_count,
            "ambiguity_score": score,
            "confidence": confidence,
            "threshold": threshold,
            "gt_classifier": gt_clf,
            "pred_classifier": pred_clf,
            "classifier_correct": int(c_ok),
        }

        for k in range(TOP_K):
            if k < len(action_candidates):
                c = action_candidates[k]
                row_data[f"top{k+1}_api_name"]    = c.get("api_name", "")
                row_data[f"top{k+1}_description"] = c.get("description", "")
                row_data[f"top{k+1}_useCase"]     = c.get("useCase", "")
                row_data[f"top{k+1}_score"]       = round(c.get("score", 0.0), 4)
                row_data[f"top{k+1}_in_doc"]      = int(_in_action_doc(c, action_doc))
            else:
                row_data[f"top{k+1}_api_name"]    = ""
                row_data[f"top{k+1}_description"] = ""
                row_data[f"top{k+1}_useCase"]     = ""
                row_data[f"top{k+1}_score"]       = ""
                row_data[f"top{k+1}_in_doc"]      = ""

        results.append(row_data)

    # ── CSV 저장 ─────────────────────────────────────────────────────────────
    with open(RESULT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(results)

    # ── 요약 ─────────────────────────────────────────────────────────────────
    scores = [r["ambiguity_score"] for r in results if r["ambiguity_score"] > 0]
    gt0_scores = [r["ambiguity_score"] for r in results if r["gt_classifier"] == 0 and r["ambiguity_score"] > 0]
    gt1_scores = [r["ambiguity_score"] for r in results if r["gt_classifier"] == 1 and r["ambiguity_score"] > 0]

    def avg(l): return round(sum(l)/len(l), 4) if l else 0.0

    print(f"\n{'='*90}")
    print(f"  [Stage1] Intent Accuracy       {intent_correct/total:.2%}  ({intent_correct}/{total})")
    print(f"  [Stage2] Classifier Accuracy   {clf_correct/total:.2%}  ({clf_correct}/{total})")
    print(f"{'─'*90}")
    print(f"  [Score]  전체 avg={avg(scores):.4f}")
    print(f"           모호(gt=0) avg={avg(gt0_scores):.4f}  ({len(gt0_scores)}건)")
    print(f"           명확(gt=1) avg={avg(gt1_scores):.4f}  ({len(gt1_scores)}건)")
    print(f"{'─'*90}")
    print(f"  결과 저장: {RESULT_CSV}")
    print(f"{'='*90}\n")


if __name__ == "__main__":
    evaluate_classifier()
