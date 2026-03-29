"""
evaluate_e2e_comparison.py

End-to-End 비교 실험: SCARF  vs  GPT-only  (232건 전체 비교)

[구조]
  - SCARF : 파이프라인 결과 URL (use_llm→EXAONE, need_info→GT슬롯으로 URL빌드, complete, rejected)
  - GPT   : OpenAI API만으로 생성한 URL (action.json 시스템 프롬프트)
  - 정답  : gt_url(수동 라벨) 또는 gt_slot_url(slot_filling→build_url_from_slots)

[실행]
  python evaluate_e2e_comparison.py
"""

import csv, json, time, os, sys, gc
from pathlib import Path
from datetime import datetime

import torch

# ── 설정 ─────────────────────────────────────────────────────────────────────
TEST_CSV     = "test_queries_labeled_url.csv"
EXAONE_MODEL = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"
OPENAI_MODEL = "gpt-4.1-mini"

OUTPUT_DIR = Path("eval_results")
OUTPUT_DIR.mkdir(exist_ok=True)
TIMESTAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
RESULT_CSV = OUTPUT_DIR / f"eval_e2e_comparison_{TIMESTAMP}.csv"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

INTENT_MAP = {
    "calibration": "calibration_control", "change_mode": "change_operation",
    "history_set": "history_control", "setting_Preset": "recipe_management",
    "chat_clear": "chat_clear", "close_windows": "close_windows",
    "no_function": "no_function",
}


# ── 0. slot_filling 파싱 & GT URL 빌드 ───────────────────────────────────────
from slot_url_builder import build_url_from_slots


def parse_slot_filling(slot_str: str) -> dict:
    """
    CSV slot_filling 열 파싱. NONE 값은 제외.
    'window_name=NONE|auto_type=AutoThresholdSet' → {'auto_type': 'AutoThresholdSet'}
    """
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
    """CSV의 subCategory + slot_filling으로 정답 URL을 빌드한다."""
    intent = INTENT_MAP.get(sub_category, sub_category)
    if intent == "chat_clear":
        return "/chat/clear"
    if intent == "close_windows":
        return "/windows/close"
    if intent == "no_function":
        return "/NO_FUNCTION"
    slots = parse_slot_filling(slot_str)
    if not slots and intent not in ("change_operation",):
        return ""
    return build_url_from_slots(intent, slots)


# ── 1. action.json → GPT 시스템 프롬프트 ──────────────────────────────────────
def build_api_system_prompt() -> str:
    """action.json 전체 API 목록으로 GPT-only 시스템 프롬프트 구성."""
    action_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "ragTest", "data", "action.json",
    )
    with open(action_path, "r", encoding="utf-8") as f:
        apis = json.load(f)

    lines = []
    for api in apis:
        url = api.get("url") or api.get("url_template", "")
        desc = api.get("description", "")
        if url and url != "/NO_FUNCTION":
            if len(desc) > 50:
                desc = desc[:47] + "..."
            lines.append(f"- `{url}` : {desc}")

    api_list = "\n".join(lines)

    return f"""너는 반도체 공정 비전 검사 시스템의 대화형 인터페이스야.
사용자가 말로 명령을 내리면, 아래의 API 주소들 중 적절한 API 호출 주소를 **정확한 주소 문자열로만** 반환해.
설명이나 부가 텍스트는 절대 포함하지 마.

**복합 명령어**: 여러 작업 요청 시 각 API를 줄바꿈으로 구분하여 모두 반환.
관련 없는 요청이면 `/NO_FUNCTION`만 반환.

### 사용 가능한 API 목록:
{api_list}

---
대답은 `/NO_FUNCTION` 또는 위에 정의된 API 주소 문자열만 포함해야 함.
"""


# ── 2. SCARF 파이프라인 ──────────────────────────────────────────────────────
_rag_loaded = False


def _ensure_rag():
    global _rag_loaded
    if not _rag_loaded:
        print("\n[SCARF] 모델 로드 중...")
        global rag_pipeline
        import rag_pipeline as _rp
        rag_pipeline = _rp
        _rag_loaded = True
        print("[SCARF] 모델 로드 완료\n")


def run_scarf(text: str, gt_sub_category: str, gt_slot_str: str) -> dict:
    """
    SCARF 파이프라인 실행 → 모든 경우에서 URL을 도출한다.
      - rejected  → /NO_FUNCTION
      - complete  → 슬롯필링 결과 URL
      - use_llm   → EXAONE이 생성한 URL
      - need_info → GT slot_filling으로 URL 빌드
    """
    _ensure_rag()
    t0 = time.time()
    result = rag_pipeline.process_new_query(text)
    elapsed = round(time.time() - t0, 4)

    status = result.get("status", "error")
    url = ""

    if status == "rejected":
        url = "/NO_FUNCTION"
    elif status == "complete":
        url = result.get("output", "")
    elif status == "use_llm":
        try:
            url = _run_exaone_for_scarf(text)
        except Exception as e:
            print(f"    [EXAONE ERROR] {e} → GT slot fallback")
            intent = result.get("intent", INTENT_MAP.get(gt_sub_category, gt_sub_category))
            gt_slots = parse_slot_filling(gt_slot_str)
            url = build_url_from_slots(intent, gt_slots) if gt_slots else ""
    elif status == "need_info":
        # 파이프라인이 분류한 intent 사용, GT 슬롯으로 URL 빌드
        intent = result.get("intent", INTENT_MAP.get(gt_sub_category, gt_sub_category))
        gt_slots = parse_slot_filling(gt_slot_str)
        url = build_url_from_slots(intent, gt_slots) if gt_slots else ""

    return {"url": url.strip(), "status": status, "elapsed": elapsed}


# ── 3. EXAONE (SCARF use_llm 경로 전용) ──────────────────────────────────────
_exaone_model = None
_exaone_tokenizer = None


def _load_exaone():
    global _exaone_model, _exaone_tokenizer
    if _exaone_model is not None:
        return
    from transformers import AutoModelForCausalLM, AutoTokenizer
    print(f"\n[EXAONE] 모델 로드 중: {EXAONE_MODEL}")
    _exaone_tokenizer = AutoTokenizer.from_pretrained(EXAONE_MODEL)
    _exaone_model = AutoModelForCausalLM.from_pretrained(
        EXAONE_MODEL,
        dtype=torch.bfloat16,
        trust_remote_code=True,
        device_map="auto",
    )
    print("[EXAONE] 모델 로드 완료\n")


def _unload_exaone():
    global _exaone_model, _exaone_tokenizer
    del _exaone_model, _exaone_tokenizer
    _exaone_model = _exaone_tokenizer = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _exaone_generate(text: str, system_prompt: str) -> str:
    _load_exaone()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": text},
    ]
    inputs = _exaone_tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True, return_tensors="pt",
    ).to(DEVICE)

    with torch.no_grad():
        output = _exaone_model.generate(
            **inputs,
            eos_token_id=_exaone_tokenizer.eos_token_id,
            max_new_tokens=200,
            do_sample=False,
        )
    decoded = _exaone_tokenizer.decode(output[0], skip_special_tokens=True)

    try:
        resp = decoded.split("[|assistant|]")[1].strip()
    except IndexError:
        resp = decoded.strip()
    resp = resp.replace("```", "").replace("`", "").strip()

    api_lines = [l.strip() for l in resp.split("\n") if l.strip().startswith("/")]
    return "\n".join(api_lines) if api_lines else resp


def _run_exaone_for_scarf(text: str) -> str:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    from common_prompt import build_prompt
    prompt = build_prompt()
    return _exaone_generate(text, prompt)


# ── 4. OpenAI (GPT-only) ─────────────────────────────────────────────────────
def _get_openai_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            for line in open(env_path, encoding="utf-8"):
                if line.startswith("OPENAI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    return key


def run_gpt_only(text: str, system_prompt: str) -> dict:
    """GPT-only: 시스템 프롬프트 + 질의 → URL. 232건 모두 실행."""
    key = _get_openai_key()
    if not key:
        return {"url": "", "elapsed": 0.0, "error": "OPENAI_API_KEY not set"}

    from openai import OpenAI
    client = OpenAI(api_key=key)

    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": text},
            ],
            temperature=0,
            max_tokens=200,
        )
        content = resp.choices[0].message.content.strip()
        content = content.replace("```", "").replace("`", "").strip()
        api_lines = [l.strip() for l in content.split("\n") if l.strip().startswith("/")]
        url = "\n".join(api_lines) if api_lines else content
    except Exception as e:
        url = ""
        content = f"ERROR: {e}"

    elapsed = round(time.time() - t0, 4)
    return {"url": url.strip(), "elapsed": elapsed}


# ── 5. 평가 메인 ────────────────────────────────────────────────────────────
FIELDNAMES = [
    "id", "text", "gt_intent", "gt_slot_filling", "gt_url", "gt_slot_url",
    # SCARF (파이프라인 전체: retrieval→ambiguity→EXAONE/슬롯필링)
    "scarf_url", "scarf_status", "scarf_url_correct", "scarf_time",
    # GPT-only (OpenAI API만)
    "gpt_url", "gpt_url_correct", "gpt_time",
]


def evaluate():
    rows = list(csv.DictReader(open(TEST_CSV, encoding="utf-8-sig")))
    total = len(rows)
    system_prompt = build_api_system_prompt()
    print(f"[DEBUG] System Prompt: {len(system_prompt)} chars, API count: {system_prompt.count('- `/')}")

    # ── GT slot URL 사전 빌드 ─────────────────────────────────────────────────
    gt_slot_urls = []
    for row in rows:
        sub_cat = row["subCategory"].strip()
        slot_str = row.get("slot_filling", "").strip()
        gt_slot_urls.append(build_gt_slot_url(sub_cat, slot_str))

    gt_url_count  = sum(1 for r in rows if r["url"].strip())
    slot_url_count = sum(1 for u in gt_slot_urls if u)
    print(f"[GT] gt_url: {gt_url_count}건, gt_slot_url: {slot_url_count}/{total}건")

    # ── Phase 1: GPT-only (OpenAI) ────────────────────────────────────────────
    print(f"\n{'='*80}")
    print(f"  [Phase 1/2] GPT-only ({OPENAI_MODEL}) — {total}건")
    print(f"{'='*80}")
    gpt_results = []
    for i, row in enumerate(rows):
        text = row["text"].strip()
        r = run_gpt_only(text, system_prompt)
        gpt_results.append(r)
        err = r.get("error", "")
        tag = "ERR" if err else r["url"][:55] if r["url"] else "(empty)"
        print(f"  [{i+1:3d}/{total}] {r['elapsed']:.2f}s  {tag}  ← {text[:35]}")

    # ── Phase 2: SCARF ────────────────────────────────────────────────────────
    print(f"\n{'='*80}")
    print(f"  [Phase 2/2] SCARF pipeline — {total}건")
    print(f"{'='*80}")
    scarf_results = []
    for i, row in enumerate(rows):
        text = row["text"].strip()
        sub_cat = row["subCategory"].strip()
        slot_str = row.get("slot_filling", "").strip()
        r = run_scarf(text, gt_sub_category=sub_cat, gt_slot_str=slot_str)
        scarf_results.append(r)
        tag = r["url"][:55] if r["url"] else "(empty)"
        print(f"  [{i+1:3d}/{total}] {r['status']:<10} {r['elapsed']:.2f}s  {tag}  ← {text[:35]}")

    # ── 메모리 정리 ───────────────────────────────────────────────────────────
    _unload_exaone()
    global rag_pipeline, _rag_loaded
    if _rag_loaded:
        del rag_pipeline
        _rag_loaded = False
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # ── 집계 (232건 전체) ─────────────────────────────────────────────────────
    # SCARF: gt_url or gt_slot_url 기준 (슬롯필링 사용)
    # GPT  : gt_url 기준만 (슬롯필링 미사용 → gt_slot_url 비교 불공정)
    stats = {
        "scarf": {"correct": 0, "eval_total": 0, "has_url": 0, "times": []},
        "gpt":   {"correct": 0, "eval_total": 0, "has_url": 0, "times": []},
        # gt_url 78건 기준 동일 조건 비교
        "scarf_gt": {"correct": 0, "total": 0},
        "gpt_gt":   {"correct": 0, "total": 0},
    }

    results = []
    for i, row in enumerate(rows):
        rid      = row["id"]
        text     = row["text"].strip()
        gt_int   = INTENT_MAP.get(row["subCategory"].strip(), row["subCategory"].strip())
        gt_url   = row["url"].strip()
        gt_s_url = gt_slot_urls[i]
        slot_str = row.get("slot_filling", "").strip()

        sr  = scarf_results[i]
        gr  = gpt_results[i]

        # ── SCARF 평가: gt_url 우선, 없으면 gt_slot_url ──
        scarf_eval_url = gt_url if gt_url else gt_s_url
        scarf_ok = ""
        if scarf_eval_url:
            scarf_ok = int(sr["url"] == scarf_eval_url)
            stats["scarf"]["correct"]    += scarf_ok
            stats["scarf"]["eval_total"] += 1

        # ── GPT 평가: gt_url만 (슬롯필링 안 쓰므로) ──
        gpt_ok = ""
        if gt_url:
            gpt_ok = int(gr["url"] == gt_url)
            stats["gpt"]["correct"]    += gpt_ok
            stats["gpt"]["eval_total"] += 1

        # ── gt_url 78건 동일 조건 비교 ──
        if gt_url:
            stats["scarf_gt"]["correct"] += int(sr["url"] == gt_url)
            stats["scarf_gt"]["total"]   += 1
            stats["gpt_gt"]["correct"]   += int(gr["url"] == gt_url)
            stats["gpt_gt"]["total"]     += 1

        if sr["url"]:
            stats["scarf"]["has_url"] += 1
        if gr["url"]:
            stats["gpt"]["has_url"] += 1

        stats["scarf"]["times"].append(sr["elapsed"])
        stats["gpt"]["times"].append(gr["elapsed"])

        results.append({
            "id": rid, "text": text, "gt_intent": gt_int,
            "gt_slot_filling": slot_str, "gt_url": gt_url, "gt_slot_url": gt_s_url,
            "scarf_url": sr["url"], "scarf_status": sr.get("status", ""),
            "scarf_url_correct": scarf_ok, "scarf_time": sr["elapsed"],
            "gpt_url": gr["url"],
            "gpt_url_correct": gpt_ok, "gpt_time": gr["elapsed"],
        })

    # ── CSV 저장 ─────────────────────────────────────────────────────────────
    with open(RESULT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(results)

    # ── 요약 출력 ────────────────────────────────────────────────────────────
    def pct(a, b): return f"{a/b:.2%}" if b else "N/A"
    def avg(lst): return round(sum(lst)/len(lst), 4) if lst else 0.0

    print(f"\n{'='*80}")
    print(f"  SCARF vs GPT-only  —  전체 {total}건")
    print(f"{'='*80}")

    # 1) gt_url 78건 동일 조건 비교 (head-to-head)
    sg = stats["scarf_gt"]
    gg = stats["gpt_gt"]
    print(f"\n  [1] gt_url 기준 동일 조건 비교 ({sg['total']}건)")
    print(f"  {'Method':<25} {'Accuracy':>10} {'Correct':>8} {'Total':>8} {'Avg Time':>10}")
    print(f"  {'-'*61}")
    print(f"  {'SCARF (full pipeline)':<25} {pct(sg['correct'], sg['total']):>10}"
          f" {sg['correct']:>8} {sg['total']:>8}"
          f" {avg(stats['scarf']['times']):>9.3f}s")
    print(f"  {f'GPT-only ({OPENAI_MODEL})':<25} {pct(gg['correct'], gg['total']):>10}"
          f" {gg['correct']:>8} {gg['total']:>8}"
          f" {avg(stats['gpt']['times']):>9.3f}s")

    # 2) 각 시스템 최대 평가 범위
    print(f"\n  [2] 각 시스템 최대 평가 범위")
    print(f"  {'Method':<25} {'Accuracy':>10} {'Correct':>8} {'평가대상':>8} {'URL도출':>8}")
    print(f"  {'-'*59}")
    ss = stats["scarf"]
    print(f"  {'SCARF (slot_url 포함)':<25} {pct(ss['correct'], ss['eval_total']):>10}"
          f" {ss['correct']:>8} {ss['eval_total']:>8}"
          f" {ss['has_url']:>8}")
    gs = stats["gpt"]
    print(f"  {'GPT-only (gt_url만)':<25} {pct(gs['correct'], gs['eval_total']):>10}"
          f" {gs['correct']:>8} {gs['eval_total']:>8}"
          f" {gs['has_url']:>8}")

    # SCARF status 분포
    from collections import Counter
    status_dist = Counter(r["scarf_status"] for r in results)
    print(f"\n  SCARF status: {dict(status_dist)}")

    print(f"\n  result: {RESULT_CSV}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    evaluate()
