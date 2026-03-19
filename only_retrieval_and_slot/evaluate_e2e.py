"""
evaluate_e2e.py

[데이터 구조]
index_Classifier=0 + url 없음  → 슬롯 경로 (모호) → Stage3a 슬롯 채점
index_Classifier=0 + url 있음  → 즉시 완성 (no_function 등) → URL 채점
index_Classifier=1              → LLM 경로 (명확) → Stage3b URL 채점

[Stage 채점]
Stage1: subCategory intent 정확도
Stage2: 모호/명확 판단 정확도
  - GT: index_Classifier (0=모호, 1=명확)
  - Pred: result["is_ambiguous"] (True=모호, False=명확)
Stage3a: 슬롯 채점 (슬롯 경로)
  - slot_accuracy       전체 슬롯(NONE 포함) 일치율
  - active_slot_accuracy GT가 NONE 아닌 슬롯만 일치율
  - sample_correct      발화 단위 전체 슬롯 일치
Stage3b: URL Exact Match (URL 경로)
"""

import csv, json, time, requests
from pathlib import Path
from datetime import datetime
from collections import defaultdict

APP_URL      = "http://localhost:5000/instruct/"
TEST_CSV     = "test_queries_labeled_url.csv"
OUTPUT_DIR   = Path("eval_results")
OUTPUT_DIR.mkdir(exist_ok=True)
TIMESTAMP    = datetime.now().strftime("%Y%m%d_%H%M%S")
DETAIL_CSV   = OUTPUT_DIR / f"eval_detail_{TIMESTAMP}.csv"
SUMMARY_JSON = OUTPUT_DIR / f"eval_summary_{TIMESTAMP}.json"

INTENT_MAP = {
    "calibration":    "calibration_control",
    "change_mode":    "change_operation",
    "history_set":    "history_control",
    "setting_Preset": "recipe_management",
    "chat_clear":     "chat_clear",
    "close_windows":  "close_windows",
    "no_function":    "no_function",
}

def parse_slots(s):
    if not s or s.strip() in ("NONE", ""):
        return {}
    out = {}
    for pair in s.strip().split("|"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            out[k.strip()] = v.strip()
    return out

def score_slots(pred, gt):
    if not gt:
        return {"slot_results":{}, "slot_accuracy":1.0, "active_accuracy":None,
                "correct":0, "total":0, "active_correct":0, "active_total":0,
                "sample_correct":True}
    keys = set(gt) | set(pred)
    total = correct = at = ac = 0
    sr = {}
    for k in keys:
        g = gt.get(k, "NONE"); p = pred.get(k, "NONE"); ok = (g == p)
        sr[k] = {"gt": g, "pred": p, "correct": ok}
        total += 1; correct += int(ok)
        if g != "NONE":
            at += 1; ac += int(ok)
    return {"slot_results": sr,
            "slot_accuracy":   correct/total if total else 0.0,
            "active_accuracy": ac/at if at else None,
            "correct": correct, "total": total,
            "active_correct": ac, "active_total": at,
            "sample_correct": correct == total}

def extract_slots(result):
    raw = result.get("slots")
    if isinstance(raw, dict) and raw:
        return {k: str(v) for k, v in raw.items()}
    if isinstance(raw, str) and raw:
        return parse_slots(raw)
    out = result.get("output", "")
    if "|" in out and "=" in out:
        return parse_slots(out)
    return {}

def call_api(text, timeout=60):
    t0 = time.time()
    try:
        r = requests.post(APP_URL, json={"text": text}, timeout=timeout)
        ct = round(time.time()-t0, 4)
        if r.status_code != 200:
            return {"status":"error","output":f"HTTP {r.status_code}","intent":"",
                    "elapsed_time":0.0,"client_time":ct,"is_ambiguous":None}
        d = r.json(); d["client_time"] = ct; return d
    except Exception as e:
        ct = round(time.time()-t0, 4)
        return {"status":"error","output":str(e),"intent":"",
                "elapsed_time":0.0,"client_time":ct,"is_ambiguous":None}

def evaluate():
    rows = list(csv.DictReader(open(TEST_CSV, encoding="utf-8-sig")))
    detail_rows = []
    st = {
        "total": 0,
        # Stage1
        "intent_correct":0, "intent_total":0,
        # Stage2
        "ambig_correct":0, "ambig_total":0,
        # Stage3a Slot
        "slot_sample_correct":0, "slot_sample_total":0,
        "slot_correct":0, "slot_total":0,
        "active_correct":0, "active_total":0,
        # Stage3b URL
        "url_correct":0, "url_total":0,
        # 시간
        "server_times":[], "client_times":[],
        "retriever_times":[], "classifier_times":[],
        "slot_times":[], "exaone_times":[],
        # intent별 오류
        "intent_err":defaultdict(int),
        "ambig_err":defaultdict(int),
        "slot_err":defaultdict(int),
        "url_err":defaultdict(int),
    }

    print(f"평가 시작 총 {len(rows)}개\n{'='*72}")

    for i, row in enumerate(rows):
        rid     = row["id"]
        text    = row["text"].strip()
        gt_int  = INTENT_MAP.get(row["subCategory"].strip(), row["subCategory"].strip())
        gt_slot = parse_slots(row["slot_filling"])
        gt_url  = row["url"].strip()
        clf     = row["index_Classifier"]

        # GT 경로 분류
        gt_is_ambig = (clf == "0")   # 0=모호(슬롯필링), 1=명확(LLM)
        is_slot     = (clf == "0" and not gt_url)   # 슬롯 채점 대상
        is_url      = (clf == "1") or (clf == "0" and bool(gt_url))  # URL 채점 대상

        st["total"] += 1
        res      = call_api(text)
        server_t = res.get("elapsed_time", 0.0)
        client_t = res.get("client_time", 0.0)
        status   = res.get("status", "error")
        output   = res.get("output", "")
        pred_int = INTENT_MAP.get(res.get("intent",""), res.get("intent",""))

        # is_ambiguous: rag_pipeline이 모호하다고 판단했는지
        # need_info → 모호, use_llm/complete(LLM경로) → 명확
        # complete이지만 slots가 있으면 슬롯 경로로 완성된 것 → 모호
        raw_ambig = res.get("is_ambiguous")
        if raw_ambig is not None:
            pred_is_ambig = bool(raw_ambig)
        else:
            # is_ambiguous 키 없으면 status로 추론
            pred_is_ambig = (status == "need_info") or \
                            (status == "complete" and bool(res.get("slots")))

        st["server_times"].append(server_t)
        st["client_times"].append(client_t)

        # 스텝별 시간
        stage_t = res.get("stage_times", {})
        if stage_t.get("retriever_s"):  st["retriever_times"].append(stage_t["retriever_s"])
        if stage_t.get("classifier_s"): st["classifier_times"].append(stage_t["classifier_s"])
        if stage_t.get("slot_s"):       st["slot_times"].append(stage_t["slot_s"])
        if stage_t.get("exaone_s"):     st["exaone_times"].append(stage_t["exaone_s"])

        # ── Stage1: Intent ────────────────────────────────────────────────────
        int_ok = (pred_int == gt_int)
        st["intent_total"]   += 1
        st["intent_correct"] += int(int_ok)
        if not int_ok:
            st["intent_err"][gt_int] += 1

        # ── Stage2: 모호/명확 판단 ────────────────────────────────────────────
        ambig_ok = (pred_is_ambig == gt_is_ambig)
        st["ambig_total"]   += 1
        st["ambig_correct"] += int(ambig_ok)
        if not ambig_ok:
            st["ambig_err"][gt_int] += 1

        # ── Stage3a: 슬롯 채점 ────────────────────────────────────────────────
        ss = {}; slot_ok = False
        if is_slot:
            pred_slots = extract_slots(res)
            ss = score_slots(pred_slots, gt_slot)
            slot_ok = ss["sample_correct"]
            st["slot_sample_total"]   += 1
            st["slot_sample_correct"] += int(slot_ok)
            st["slot_total"]          += ss["total"]
            st["slot_correct"]        += ss["correct"]
            st["active_total"]        += ss["active_total"]
            st["active_correct"]      += ss["active_correct"]
            if not slot_ok:
                st["slot_err"][gt_int] += 1

        # ── Stage3b: URL 채점 ─────────────────────────────────────────────────
        url_ok = False; pred_url = ""
        if is_url:
            pred_url = output.strip() if status in ("complete","rejected") else ""
            url_ok   = (pred_url == gt_url)
            st["url_total"]   += 1
            st["url_correct"] += int(url_ok)
            if not url_ok:
                st["url_err"][gt_int] += 1

        # 출력
        main_ok = slot_ok if is_slot else url_ok
        tag = "SLOT" if is_slot else "URL "
        print(f"[{i+1:3d}/{len(rows)}] {'O' if main_ok else 'X'} id={rid:>3} "
              f"I={'O' if int_ok else 'X'} "
              f"A={'O' if ambig_ok else 'X'} "
              f"{tag}={'O' if main_ok else 'X'} "
              f"status={status:<9} {client_t:.2f}s  {text[:32]}")

        detail_rows.append({
            "id": rid, "text": text,
            "route": "slot" if is_slot else "url",
            "index_Classifier": clf,
            # Stage1
            "gt_intent": gt_int, "pred_intent": pred_int,
            "intent_correct": int(int_ok),
            # Stage2
            "gt_is_ambiguous": int(gt_is_ambig),
            "pred_is_ambiguous": int(pred_is_ambig),
            "ambig_correct": int(ambig_ok),
            # Stage3a
            "gt_slots": row["slot_filling"],
            "pred_slots": json.dumps(ss.get("slot_results",{}), ensure_ascii=False) if ss else "",
            "slot_accuracy": round(ss.get("slot_accuracy",0.0),4) if ss else "",
            "active_slot_accuracy": round(ss.get("active_accuracy") or 0.0,4) if ss else "",
            "slot_all_correct": int(slot_ok) if is_slot else "",
            # Stage3b
            "gt_url": gt_url, "pred_url": pred_url,
            "url_correct": int(url_ok) if is_url else "",
            # 기타
            "server_time_s": server_t, "client_time_s": client_t,
            "pipeline_status": status,
        })

    # 집계
    def pct(a,b): return round(a/b,4) if b else 0.0
    def avg(l):   return round(sum(l)/len(l),4) if l else 0.0
    def pxx(l,p): return round(sorted(l)[int(len(l)*p)],4) if l else 0.0

    summary = {
        "timestamp": TIMESTAMP, "total_samples": st["total"],
        "stage1_intent": {
            "accuracy": pct(st["intent_correct"],st["intent_total"]),
            "correct": st["intent_correct"], "total": st["intent_total"],
            "errors_by_intent": dict(st["intent_err"])},
        "stage2_ambiguity": {
            "accuracy": pct(st["ambig_correct"],st["ambig_total"]),
            "correct": st["ambig_correct"], "total": st["ambig_total"],
            "errors_by_intent": dict(st["ambig_err"])},
        "stage3a_slot": {
            "sample_accuracy":      pct(st["slot_sample_correct"],st["slot_sample_total"]),
            "slot_accuracy":        pct(st["slot_correct"],st["slot_total"]),
            "active_slot_accuracy": pct(st["active_correct"],st["active_total"]),
            "sample_correct": st["slot_sample_correct"], "sample_total": st["slot_sample_total"],
            "slot_correct": st["slot_correct"], "slot_total": st["slot_total"],
            "active_correct": st["active_correct"], "active_total": st["active_total"],
            "errors_by_intent": dict(st["slot_err"])},
        "stage3b_url": {
            "accuracy": pct(st["url_correct"],st["url_total"]),
            "correct": st["url_correct"], "total": st["url_total"],
            "errors_by_intent": dict(st["url_err"])},
        "latency": {
            "server_avg_s": avg(st["server_times"]),
            "server_p50_s": pxx(st["server_times"],0.50),
            "server_p95_s": pxx(st["server_times"],0.95),
            "client_avg_s": avg(st["client_times"]),
            "client_p50_s": pxx(st["client_times"],0.50),
            "client_p95_s": pxx(st["client_times"],0.95)},
        "stage_latency": {
            "retriever_avg_s":  avg(st["retriever_times"]),
            "classifier_avg_s": avg(st["classifier_times"]),
            "slot_avg_s":       avg(st["slot_times"]),
            "exaone_avg_s":     avg(st["exaone_times"]),
        },
    }

    with open(DETAIL_CSV,"w",newline="",encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(detail_rows[0].keys()))
        w.writeheader(); w.writerows(detail_rows)
    with open(SUMMARY_JSON,"w",encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    s = summary
    print(f"\n{'='*72}")
    print(f"  총 {st['total']}개  (슬롯경로: {st['slot_sample_total']} / URL경로: {st['url_total']})")
    print(f"{'─'*72}")
    print(f"  [Stage1] Intent Accuracy              {s['stage1_intent']['accuracy']:.2%}  ({st['intent_correct']}/{st['intent_total']})")
    print(f"  [Stage2] Ambiguity Accuracy           {s['stage2_ambiguity']['accuracy']:.2%}  ({st['ambig_correct']}/{st['ambig_total']})")
    print(f"{'─'*72}")
    print(f"  [Stage3a] Slot Sample Accuracy        {s['stage3a_slot']['sample_accuracy']:.2%}  ({st['slot_sample_correct']}/{st['slot_sample_total']})")
    print(f"  [Stage3a] All Slot Accuracy           {s['stage3a_slot']['slot_accuracy']:.2%}  ({st['slot_correct']}/{st['slot_total']})")
    print(f"  [Stage3a] Active Slot Accuracy        {s['stage3a_slot']['active_slot_accuracy']:.2%}  ({st['active_correct']}/{st['active_total']})")
    print(f"{'─'*72}")
    print(f"  [Stage3b] URL Exact Match             {s['stage3b_url']['accuracy']:.2%}  ({st['url_correct']}/{st['url_total']})")
    print(f"{'─'*72}")
    print(f"  [Latency] server avg={s['latency']['server_avg_s']:.3f}s  p50={s['latency']['server_p50_s']:.3f}s  p95={s['latency']['server_p95_s']:.3f}s")
    sl = s['stage_latency']
    print(f"{'─'*72}")
    print(f"  [Stage Latency]")
    print(f"    Retriever  avg={sl['retriever_avg_s']:.3f}s")
    print(f"    Classifier avg={sl['classifier_avg_s']:.3f}s")
    print(f"    Slot       avg={sl['slot_avg_s']:.3f}s")
    print(f"    EXAONE     avg={sl['exaone_avg_s']:.3f}s")
    print(f"  상세: {DETAIL_CSV}\n  요약: {SUMMARY_JSON}")
    print(f"{'='*72}\n")
    return summary

if __name__ == "__main__":
    evaluate()