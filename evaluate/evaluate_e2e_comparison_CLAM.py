"""
evaluate_e2e_comparison_CLAM.py

CLAM (Contrastive Learning with Ambiguity Management) 단독 평가

[비교 구도]
  SCARF  : Retrieval → BGE 분류기 → EXAONE / RoBERTa 슬롯 필링  (파인튜닝 파이프라인)
  ProCoT : Thought → Action → Response  (GPT-5.4, 전체 API 목록 주입)
  CLAM   : Stage1 KoE5 Retrieve → GPT-5.4 top-k 동적 주입  (본 파일)

[CLAM vs ProCoT 차이]
  - Stage1 KoE5 retriever가 top-k 문서를 검색 → user 메시지에 동적 주입
  - 전체 API 목록 대신 쿼리별 상위 k개 후보만 LLM에 전달
  - 그 외 평가 지표·멀티턴 구조·mock answer 방식은 ProCoT와 동일

[평가 지표]
  1) CNP Accuracy   : 모호(GT=0)→CLARIFY, 명확(GT=1)→EXECUTE 정확도 (1차 판정)
  2) Safety Rate    : GT=0(모호) 중 CLARIFY 선택 비율
  3) False Block    : GT=1(명확) 중 CLARIFY 선택 비율
  4) URL Exact Match: EXECUTE 최종 결과 URL 정확도 (미생성=오답)
  5) Multi-turn 통계: 평균 턴 수, 턴별 분포
  6) 95% CI (Wilson score)

[실행]
  python evaluate_e2e_comparison_CLAM.py
"""

import csv
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from collections import Counter

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from slot_url_builder import build_url_from_slots
from clam_pipeline import run_clam, build_clam_system_prompt

# ── 설정 ──────────────────────────────────────────────────────────────────────
TEST_CSV   = str(PROJECT_ROOT / "test_queries_labeled_url.csv")
OUTPUT_DIR = PROJECT_ROOT / "eval_results"
OUTPUT_DIR.mkdir(exist_ok=True)
TIMESTAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
RESULT_CSV = OUTPUT_DIR / f"eval_clam_{TIMESTAMP}.csv"

INTENT_MAP = {
    "calibration":    "calibration_control",
    "change_mode":    "change_operation",
    "history_set":    "history_control",
    "setting_Preset": "recipe_management",
    "chat_clear":     "chat_clear",
    "close_windows":  "close_windows",
    "no_function":    "no_function",
}


# ── GT slot URL 빌더 ───────────────────────────────────────────────────────────
def _parse_slot_filling(slot_str: str) -> dict:
    if not slot_str or slot_str.strip() == "NONE":
        return {}
    slots = {}
    for pair in slot_str.strip().split("|"):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        k, v = k.strip(), v.strip()
        if v and v != "NONE":
            slots[k] = v
    return slots


def build_gt_slot_url(sub_category: str, slot_str: str) -> str:
    intent = INTENT_MAP.get(sub_category, sub_category)
    if intent == "chat_clear":
        return "/chat/clear"
    if intent == "close_windows":
        return "/windows/close"
    if intent == "no_function":
        return "/NO_FUNCTION"
    slots = _parse_slot_filling(slot_str)
    if not slots and intent not in ("change_operation",):
        return ""
    return build_url_from_slots(intent, slots)


# ── Wilson CI ─────────────────────────────────────────────────────────────────
def _wilson_ci(correct: int, total: int, z: float = 1.96) -> tuple:
    if total == 0:
        return (0.0, 0.0)
    p = correct / total
    denom  = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    spread = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denom
    return (round(max(0, center - spread), 4), round(min(1, center + spread), 4))


# ── 평가 메인 ──────────────────────────────────────────────────────────────────
def evaluate():
    rows  = list(csv.DictReader(open(TEST_CSV, encoding="utf-8-sig")))
    total = len(rows)

    system_prompt = build_clam_system_prompt()
    print(f"[CLAM] System prompt: {len(system_prompt)} chars")

    # GT slot URL 사전 빌드
    gt_slot_urls = []
    for row in rows:
        gt_slot_urls.append(
            build_gt_slot_url(row["subCategory"].strip(), row.get("slot_filling", "").strip())
        )

    print(f"\n{'='*80}")
    print(f"  CLAM (gpt-5.4, top-k 동적 주입) — {total}건  (max {10} turns)")
    print(f"{'='*80}")

    clam_results = []
    for i, row in enumerate(rows):
        text     = row["text"].strip()
        slot_str = row.get("slot_filling", "").strip()
        url_str  = row.get("url", "").strip()

        r = run_clam(text, system_prompt, gt_slot_str=slot_str, gt_url=url_str)
        clam_results.append(r)

        err       = r.get("error", "")
        tc        = r.get("turn_count", 1)
        first_a   = r.get("first_action", r["action"])
        final_a   = r["action"]
        action_tag = f"{first_a}>{final_a}" if first_a != final_a else first_a
        tc_tag    = f" T{tc}" if tc > 1 else "   "
        url_tag   = r["url"][:40] if r["url"] else "(no url)"
        print(f"  [{i+1:3d}/{total}] {r['elapsed']:.2f}s  "
              f"{action_tag:<17}{tc_tag} {url_tag}  <- {text[:30]}"
              f"{'  ' + err if err else ''}")

    # ── 집계 ──────────────────────────────────────────────────────────────────
    stats = {
        "cnp_correct": 0, "cnp_total": 0,
        "safety_correct": 0, "safety_total": 0,
        "false_block": 0, "false_block_total": 0,
        "url_correct": 0, "url_total": 0,
        "has_url": 0, "times": [], "turn_counts": [],
    }

    results = []
    for i, row in enumerate(rows):
        rid      = row["id"]
        text     = row["text"].strip()
        gt_int   = INTENT_MAP.get(row["subCategory"].strip(), row["subCategory"].strip())
        gt_clf   = int(row["index_Classifier"])   # 0=모호, 1=명확
        gt_url   = row["url"].strip()
        gt_s_url = gt_slot_urls[i]
        slot_str = row.get("slot_filling", "").strip()

        r        = clam_results[i]
        eval_url = gt_url if gt_url else gt_s_url

        # ── CNP: first_action(1차 판정) 기준 ──
        first_action = r.get("first_action", r["action"])
        if gt_clf == 0:
            cnp_ok = int(first_action == "CLARIFY")
            stats["safety_correct"] += cnp_ok
            stats["safety_total"]   += 1
        else:
            cnp_ok = int(first_action != "CLARIFY")
            if first_action == "CLARIFY":
                stats["false_block"] += 1
            stats["false_block_total"] += 1
        stats["cnp_correct"] += cnp_ok
        stats["cnp_total"]   += 1

        # ── URL: 최종 action 기준, 미생성=오답 ──
        clam_url_ok = ""
        if eval_url:
            clam_url_ok = int(r["url"] == eval_url) if r["url"] else 0
            stats["url_correct"] += clam_url_ok
            stats["url_total"]   += 1

        if r["url"]:
            stats["has_url"] += 1
        stats["times"].append(r["elapsed"])
        stats["turn_counts"].append(r.get("turn_count", 1))

        clam_cnp = int(
            (gt_clf == 0 and first_action == "CLARIFY") or
            (gt_clf == 1 and first_action != "CLARIFY")
        )

        results.append({
            "id": rid, "text": text,
            "gt_intent": gt_int, "gt_classifier": gt_clf,
            "gt_slot_filling": slot_str, "gt_url": gt_url, "gt_slot_url": gt_s_url,
            # CLAM
            "clam_sub_category":      r.get("sub_category", ""),
            "clam_first_action":      first_action,
            "clam_final_action":      r["action"],
            "clam_url":               r["url"],
            "clam_thought":           r.get("thought", "")[:200],
            "clam_url_correct":       clam_url_ok,
            "clam_cnp_correct":       clam_cnp,
            "clam_time":              r["elapsed"],
            "clam_turn_count":        r.get("turn_count", 1),
            "clam_clarify_questions": "; ".join(r.get("clarify_questions", []))[:300],
        })

    # ── CSV 저장 ───────────────────────────────────────────────────────────────
    fieldnames = [
        "id", "text", "gt_intent", "gt_classifier", "gt_slot_filling",
        "gt_url", "gt_slot_url",
        "clam_sub_category", "clam_first_action", "clam_final_action",
        "clam_url", "clam_thought", "clam_url_correct", "clam_cnp_correct",
        "clam_time", "clam_turn_count", "clam_clarify_questions",
    ]
    with open(RESULT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)

    # ── 요약 출력 ──────────────────────────────────────────────────────────────
    def pct(a, b): return f"{a/b:.2%}" if b else "N/A"
    def avg(lst):  return round(sum(lst) / len(lst), 4) if lst else 0.0

    s = stats
    print(f"\n{'='*80}")
    print(f"  CLAM (gpt-5.4, top-k 동적 주입) 단독 평가  —  {total}건")
    print(f"{'='*80}")

    # 1) CNP
    print(f"\n  [1] Clarification Need Prediction (CNP) — 1차 판정 기준")
    print(f"  {'Metric':<25} {'Value':>10}")
    print(f"  {'-'*35}")
    print(f"  {'CNP Accuracy':<25} {pct(s['cnp_correct'], s['cnp_total']):>10}")
    print(f"  {'Safety Rate':<25} {pct(s['safety_correct'], s['safety_total']):>10}")
    print(f"  {'False Block Rate':<25} {pct(s['false_block'], s['false_block_total']):>10}")
    print(f"  {'Avg Latency':<25} {avg(s['times']):>9.3f}s")

    # 2) URL
    print(f"\n  [2] URL Exact Match — 멀티턴 최종 결과 (미생성=오답)")
    print(f"  {'Metric':<25} {'Value':>10}")
    print(f"  {'-'*35}")
    print(f"  {'Accuracy':<25} {pct(s['url_correct'], s['url_total']):>10}")
    print(f"  {'Correct':<25} {s['url_correct']:>10}")
    print(f"  {'Total (evaluated)':<25} {s['url_total']:>10}")
    print(f"  {'URL 생성 건수':<25} {s['has_url']:>10}")
    no_url = s["url_total"] - s["has_url"]
    if no_url > 0:
        print(f"  {'URL 미생성 (=오답)':<25} {no_url:>10}")

    # 3) Action 분포
    print(f"\n  [3] Action 분포")
    first_actions = Counter(r["clam_first_action"] for r in results)
    final_actions = Counter(r["clam_final_action"]  for r in results)
    print(f"  1차 판정: {dict(first_actions)}")
    print(f"  최종:     {dict(final_actions)}")

    # 4) Multi-turn
    tc_list = s["turn_counts"]
    tc_dist = Counter(tc_list)
    print(f"\n  [4] Multi-turn 통계")
    print(f"  평균 턴 수: {avg(tc_list):.2f}")
    for t in sorted(tc_dist.keys()):
        print(f"    {t}턴: {tc_dist[t]}건")

    print(f"\n  GT 분포: 모호(0)={sum(1 for r in rows if r['index_Classifier']=='0')}건,"
          f" 명확(1)={sum(1 for r in rows if r['index_Classifier']=='1')}건")

    # 5) 95% CI
    print(f"\n  [5] 95% Confidence Intervals (Wilson Score)")
    cnp_ci = _wilson_ci(s["cnp_correct"], s["cnp_total"])
    print(f"  CNP Accuracy: {s['cnp_correct']}/{s['cnp_total']}"
          f" = {pct(s['cnp_correct'], s['cnp_total'])}  CI={cnp_ci}")
    if s["url_total"]:
        url_ci = _wilson_ci(s["url_correct"], s["url_total"])
        print(f"  URL EM:       {s['url_correct']}/{s['url_total']}"
              f" = {pct(s['url_correct'], s['url_total'])}  CI={url_ci}")

    print(f"\n  result: {RESULT_CSV}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    evaluate()
