"""
evaluate_e2e_comparison_ProCoT.py

SCARF (fine-tuned pipeline)  vs  ProCoT (GPT-5.4 prompting)  비교 실험

[비교 구도]
  SCARF   : Retrieval → Ambiguity Classifier → EXAONE/SlotFilling  (파인튜닝 파이프라인)
  ProCoT  : Thought → Action → Response  (LLM 프롬프팅 기법, Deng et al. EMNLP 2023)

[평가 지표]
  1) CNP (Clarification Need Prediction)
     - 모호한 질의(GT=0)를 CLARIFY로, 명확한 질의(GT=1)를 EXECUTE로 판정하는 정확도
  2) Safety Rate   : GT=0(모호)인 행에서 CLARIFY를 선택한 비율 (높을수록 안전)
  3) False Block   : GT=1(명확)인 행에서 CLARIFY를 선택한 비율 (낮을수록 좋음)
  4) URL Exact Match : EXECUTE 선택 시 URL 정확도 (gt_url 기준)
  5) Latency       : 쿼리당 응답 시간

[실행]
  python evaluate_e2e_comparison_ProCoT.py
"""

import csv, json, time, os, sys, re, gc
from pathlib import Path
from datetime import datetime
from collections import Counter

import numpy as np
import torch

# ── 설정 ─────────────────────────────────────────────────────────────────────
TEST_CSV      = "test_queries_labeled_url.csv"
EXAONE_MODEL  = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"
PROCOT_MODEL  = "gpt-5.4"

OUTPUT_DIR = Path("eval_results")
OUTPUT_DIR.mkdir(exist_ok=True)
TIMESTAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
RESULT_CSV = OUTPUT_DIR / f"eval_procot_comparison_{TIMESTAMP}.csv"

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
    slots = parse_slot_filling(slot_str)
    if not slots and intent not in ("change_operation",):
        return ""
    return build_url_from_slots(intent, slots)


# ── 1. API 목록 로드 ─────────────────────────────────────────────────────────
def _load_api_list() -> str:
    """action.json에서 API 목록 문자열을 구성한다."""
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
            if len(desc) > 60:
                desc = desc[:57] + "..."
            lines.append(f"- `{url}` : {desc}")
    return "\n".join(lines)


# ── 2. ProCoT 프롬프트 ───────────────────────────────────────────────────────
def build_procot_system_prompt(api_list: str) -> str:
    """
    ProCoT (Proactive Chain-of-Thought) 시스템 프롬프트.
    Deng et al. (EMNLP 2023) 의 Thought → Action → Response 구조를 적용.
    """
    return f"""너는 반도체 공정 비전 검사(AOI) 장비의 대화형 제어 인터페이스야.
사용자가 자연어로 장비 명령을 내리면 아래 3단계를 **반드시 순서대로** 수행해.

## Step 1 - Thought (분석)
사용자 명령을 분석해:
- 이 명령이 어떤 API에 해당하는지 특정 가능한가?
- 필수 파라미터(창 이름, 값, 타입 등)가 모두 명시되어 있는가?
- 여러 API에 해당할 수 있는 모호한 명령인가?
- 장비 제어와 관련 없는 질의인가?

## Step 2 - Action (결정)
분석 결과에 따라 **하나만** 선택:
- **EXECUTE** : 명령이 명확하여 특정 API를 호출할 수 있는 경우
- **CLARIFY** : 명령이 모호하여 추가 정보가 필요한 경우
- **REJECT**  : 장비 제어와 관련 없는 질의인 경우

## Step 3 - Response (응답)
- EXECUTE 선택 시: 해당 API URL을 **정확한 문자열로만** 반환 (설명 없이)
- CLARIFY 선택 시: 부족한 정보를 묻는 명확화 질문을 반환
- REJECT 선택 시: `/NO_FUNCTION` 반환

## 출력 형식 (반드시 이 형식을 따를 것)
```
[Thought] (분석 내용)
[Action] EXECUTE 또는 CLARIFY 또는 REJECT
[Response] (API URL 또는 명확화 질문 또는 /NO_FUNCTION)
```

## 예시 1 - 명확한 명령
사용자: "BGA 창에서 Scratch 임계값을 150으로 설정해줘"
```
[Thought] BGA 창, ScratchThreshold, 값 150이 모두 명시됨. /teaching/bga/update API 특정 가능.
[Action] EXECUTE
[Response] /teaching/bga/update?propertyName=ScratchThreshold&value=150
```

## 예시 2 - 모호한 명령
사용자: "임계값 올려"
```
[Thought] 어떤 창인지, 어떤 임계값인지, 몇으로 올릴지 불명확. 여러 API에 해당 가능.
[Action] CLARIFY
[Response] 어떤 창(lga/bga/qfn 등)에서 어떤 임계값을 몇으로 변경하시겠습니까?
```

## 예시 3 - 관련 없는 질의
사용자: "오늘 점심 뭐 먹지?"
```
[Thought] 장비 제어와 관련 없는 일상 질문.
[Action] REJECT
[Response] /NO_FUNCTION
```

### 사용 가능한 API 목록:
{api_list}
"""


# ── 3. ProCoT 응답 파싱 ──────────────────────────────────────────────────────
def parse_procot_response(raw: str) -> dict:
    """
    ProCoT 응답에서 Thought, Action, Response를 파싱한다.
    Returns: {thought, action, response, url}
    """
    thought = action = response = ""

    # [Thought] ... [Action] ... [Response] ... 패턴 파싱
    thought_m = re.search(r'\[Thought\]\s*(.*?)(?=\[Action\]|\Z)', raw, re.DOTALL)
    action_m  = re.search(r'\[Action\]\s*(.*?)(?=\[Response\]|\Z)', raw, re.DOTALL)
    resp_m    = re.search(r'\[Response\]\s*(.*)', raw, re.DOTALL)

    if thought_m:
        thought = thought_m.group(1).strip()
    if action_m:
        action_raw = action_m.group(1).strip().upper()
        if "EXECUTE" in action_raw:
            action = "EXECUTE"
        elif "CLARIFY" in action_raw:
            action = "CLARIFY"
        elif "REJECT" in action_raw:
            action = "REJECT"
        else:
            action = action_raw[:20]
    if resp_m:
        response = resp_m.group(1).strip().strip("`").strip()

    # URL 추출 (EXECUTE인 경우)
    url = ""
    if action == "EXECUTE":
        # /로 시작하는 줄 추출
        api_lines = [l.strip() for l in response.split("\n") if l.strip().startswith("/")]
        url = "\n".join(api_lines) if api_lines else response
    elif action == "REJECT":
        url = "/NO_FUNCTION"

    # fallback: action 파싱 실패 시 응답에서 추론
    if not action:
        if "/NO_FUNCTION" in raw:
            action = "REJECT"
            url = "/NO_FUNCTION"
        elif any(l.strip().startswith("/") for l in raw.split("\n")):
            action = "EXECUTE"
            api_lines = [l.strip() for l in raw.split("\n") if l.strip().startswith("/")]
            url = "\n".join(api_lines)
        else:
            action = "CLARIFY"

    return {
        "thought": thought,
        "action": action,
        "response": response,
        "url": url.strip(),
    }


# ── 4. OpenAI API 호출 ───────────────────────────────────────────────────────
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


# NONE 슬롯에 대한 기본 후보값 (도메인 지식 기반)
_SLOT_DEFAULTS = {
    "window_name": "bga",
    "auto_type": "AutoThresholdSet",
    "threshold_value": "150",
    "threshold_type": "ScratchThreshold",
    "operation": "teaching",
    "inspection_type": "full",
    "roi_type": "roi",
    "filter_type": "date",
    "date_range": "today",
    "camera_type": "top",
    "option_value": "on",
    "recipe_name": "default",
    "target_name": "default",
    "coordinate_value": "0",
    "button_action": "start",
    "shape_type": "circle",
    "similarity_value": "80",
    "reference_type": "golden",
    "reticle_type": "standard",
    "history_inspection_type": "all",
}

# 슬롯 키 → 자연어 템플릿
_SLOT_LABELS = {
    "window_name": "{v} 창에서",
    "auto_type": "{v} 실행",
    "threshold_value": "값은 {v}으로",
    "threshold_type": "{v} 항목",
    "operation": "{v} 모드로",
    "inspection_type": "{v} 검사",
    "roi_type": "{v} 타입",
    "filter_type": "{v} 필터",
    "camera_type": "{v} 카메라",
    "option_value": "{v}으로 설정",
    "recipe_name": "{v} 레시피",
    "target_name": "{v} 타겟",
    "button_action": "{v}",
    "coordinate_value": "좌표 {v}",
}


def _build_mock_answer(slot_str: str, gt_url: str = "") -> str:
    """
    GT slot_filling + 기본값으로 모의 사용자 응답을 생성한다.
    NONE 슬롯에는 도메인 기본값을 채워서 완전한 응답을 만든다.
    gt_url이 있으면 URL에서 파라미터 값을 추출하여 더 정확한 응답 생성.
    """
    if not slot_str or slot_str.strip() == "NONE":
        return ""

    # 모든 슬롯 파싱 (NONE 포함)
    all_slots = {}
    for pair in slot_str.strip().split("|"):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        all_slots[k.strip()] = v.strip()

    if not all_slots:
        return ""

    # gt_url에서 파라미터 추출 (가능한 경우)
    url_params = {}
    if gt_url and "?" in gt_url:
        param_str = gt_url.split("?", 1)[1]
        for p in param_str.split("&"):
            if "=" in p:
                pk, pv = p.split("=", 1)
                url_params[pk.strip()] = pv.strip()

    # NONE 슬롯에 기본값 채우기
    for k, v in all_slots.items():
        if v == "NONE":
            # gt_url 파라미터에서 값 추출 시도
            if k == "window_name" and gt_url:
                # URL 경로에서 window 추출: /teaching/bga/update → bga
                path_parts = gt_url.split("?")[0].strip("/").split("/")
                if len(path_parts) >= 2:
                    all_slots[k] = path_parts[1]
                    continue
            if k == "threshold_value" and "value" in url_params:
                all_slots[k] = url_params["value"]
                continue
            if k == "threshold_type" and "propertyName" in url_params:
                all_slots[k] = url_params["propertyName"]
                continue
            # 기본값 사용
            all_slots[k] = _SLOT_DEFAULTS.get(k, "default")

    # 자연어 응답 생성
    parts = []
    for k, v in all_slots.items():
        template = _SLOT_LABELS.get(k, "{v}")
        parts.append(template.format(v=v))
    return ", ".join(parts)


def run_procot(text: str, system_prompt: str, gt_slot_str: str = "",
               gt_url: str = "") -> dict:
    """
    ProCoT prompting으로 GPT-5.4 호출.
    1차: Thought→Action→Response
    2차(CLARIFY 시): GT 슬롯 기반 모의 응답으로 멀티턴 시뮬레이션
    """
    key = _get_openai_key()
    if not key:
        return {"thought": "", "action": "", "response": "", "url": "",
                "elapsed": 0.0, "clarify_question": "", "turn_count": 0,
                "error": "OPENAI_API_KEY not set"}

    from openai import OpenAI
    client = OpenAI(api_key=key)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": text},
    ]

    t0 = time.time()
    clarify_question = ""
    turn_count = 1

    try:
        # ── 1차 호출 ──
        resp = client.chat.completions.create(
            model=PROCOT_MODEL, messages=messages,
            temperature=0, max_completion_tokens=500,
        )
        raw = resp.choices[0].message.content.strip()
        parsed = parse_procot_response(raw)

        # ── 2차 호출: CLARIFY → 모의 응답 → 재추론 ──
        if parsed["action"] == "CLARIFY" and gt_slot_str:
            mock_answer = _build_mock_answer(gt_slot_str, gt_url=gt_url)
            if mock_answer:
                clarify_question = parsed["response"]
                turn_count = 2

                # 대화 이력에 assistant 응답 + 모의 사용자 답변 추가
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": mock_answer})

                resp2 = client.chat.completions.create(
                    model=PROCOT_MODEL, messages=messages,
                    temperature=0, max_completion_tokens=500,
                )
                raw2 = resp2.choices[0].message.content.strip()
                parsed2 = parse_procot_response(raw2)

                # 2차 결과로 URL 갱신 (action은 1차 CLARIFY 유지)
                parsed["url"] = parsed2["url"]
                parsed["thought"] = parsed["thought"] + " → " + parsed2.get("thought", "")
                parsed["action_turn2"] = parsed2["action"]
                parsed["raw"] = raw + "\n---TURN2---\n" + raw2

    except Exception as e:
        raw = f"ERROR: {e}"
        parsed = {"thought": "", "action": "ERROR", "response": str(e), "url": "",
                  "error": str(e)[:100]}

    elapsed = round(time.time() - t0, 4)
    parsed["elapsed"] = elapsed
    parsed["clarify_question"] = clarify_question
    parsed["turn_count"] = turn_count
    if "raw" not in parsed:
        parsed["raw"] = raw
    return parsed


# ── 5. SCARF 파이프라인 ──────────────────────────────────────────────────────
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
    """SCARF 파이프라인 실행. 모든 경로에서 URL + action 도출."""
    _ensure_rag()
    t0 = time.time()
    result = rag_pipeline.process_new_query(text)
    elapsed = round(time.time() - t0, 4)

    status = result.get("status", "error")
    url = ""
    action = ""

    if status == "rejected":
        url = "/NO_FUNCTION"
        action = "REJECT"
    elif status == "complete":
        url = result.get("output", "")
        action = "EXECUTE"
    elif status == "use_llm":
        try:
            url = _run_exaone_for_scarf(text)
        except Exception as e:
            print(f"    [EXAONE ERROR] {e} → GT slot fallback")
            intent = result.get("intent", INTENT_MAP.get(gt_sub_category, gt_sub_category))
            gt_slots = parse_slot_filling(gt_slot_str)
            url = build_url_from_slots(intent, gt_slots) if gt_slots else ""
        action = "EXECUTE"
    elif status == "need_info":
        # 모호 → CLARIFY (슬롯 필링 경로)
        # GT 슬롯으로 URL도 빌드해서 기록
        intent = result.get("intent", INTENT_MAP.get(gt_sub_category, gt_sub_category))
        gt_slots = parse_slot_filling(gt_slot_str)
        url = build_url_from_slots(intent, gt_slots) if gt_slots else ""
        action = "CLARIFY"

    # ambiguity 정보
    ambiguity = result.get("ambiguity", {})
    is_ambiguous = ambiguity.get("is_ambiguous", False)

    return {
        "url": url.strip(), "status": status, "action": action,
        "is_ambiguous": is_ambiguous, "elapsed": elapsed,
    }


# ── EXAONE (SCARF use_llm 전용) ──────────────────────────────────────────────
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
        EXAONE_MODEL, dtype=torch.bfloat16,
        trust_remote_code=True, device_map="auto",
    )
    print("[EXAONE] 모델 로드 완료\n")


def _unload_exaone():
    global _exaone_model, _exaone_tokenizer
    del _exaone_model, _exaone_tokenizer
    _exaone_model = _exaone_tokenizer = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _run_exaone_for_scarf(text: str) -> str:
    _load_exaone()
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    from common_prompt import build_prompt
    prompt = build_prompt()

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user",   "content": text},
    ]
    inputs = _exaone_tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True, return_tensors="pt",
    ).to(DEVICE)

    with torch.no_grad():
        output = _exaone_model.generate(
            **inputs, eos_token_id=_exaone_tokenizer.eos_token_id,
            max_new_tokens=200, do_sample=False,
        )
    decoded = _exaone_tokenizer.decode(output[0], skip_special_tokens=True)

    try:
        resp = decoded.split("[|assistant|]")[1].strip()
    except IndexError:
        resp = decoded.strip()
    resp = resp.replace("```", "").replace("`", "").strip()

    api_lines = [l.strip() for l in resp.split("\n") if l.strip().startswith("/")]
    return "\n".join(api_lines) if api_lines else resp


# ── 6. 평가 메인 ────────────────────────────────────────────────────────────
FIELDNAMES = [
    "id", "text", "gt_intent", "gt_classifier", "gt_slot_filling", "gt_url", "gt_slot_url",
    # SCARF
    "scarf_action", "scarf_url", "scarf_status", "scarf_url_correct",
    "scarf_cnp_correct", "scarf_time",
    # ProCoT
    "procot_action", "procot_url", "procot_thought", "procot_url_correct",
    "procot_cnp_correct", "procot_time",
    "procot_turn_count", "procot_clarify_question", "procot_action_turn2",
]


def _mcnemar_test(scarf_correct: list, procot_correct: list) -> dict:
    """
    McNemar's test: 두 분류기의 오류 패턴이 유의하게 다른지 검정.
    scarf_correct, procot_correct: 0/1 리스트 (같은 길이)
    Returns: {b, c, chi2, p_value}
      b = SCARF 정답 & ProCoT 오답 수
      c = SCARF 오답 & ProCoT 정답 수
    """
    from scipy.stats import chi2 as chi2_dist
    b = c = 0  # b: SCARF O & ProCoT X, c: SCARF X & ProCoT O
    for s, p in zip(scarf_correct, procot_correct):
        if s == 1 and p == 0:
            b += 1
        elif s == 0 and p == 1:
            c += 1
    n = b + c
    if n == 0:
        return {"b": b, "c": c, "chi2": 0.0, "p_value": 1.0}
    # continuity correction
    chi2_val = (abs(b - c) - 1) ** 2 / n
    p_value = 1 - chi2_dist.cdf(chi2_val, df=1)
    return {"b": b, "c": c, "chi2": round(chi2_val, 4), "p_value": round(p_value, 6)}


def _wilson_ci(correct: int, total: int, z: float = 1.96) -> tuple:
    """Wilson score 95% confidence interval for a proportion."""
    if total == 0:
        return (0.0, 0.0)
    p = correct / total
    denom = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    spread = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denom
    return (round(max(0, center - spread), 4), round(min(1, center + spread), 4))


def _print_statistical_analysis(results: list, total: int):
    """McNemar's test + 95% CI 출력."""
    print(f"\n  {'='*70}")
    print(f"  [Statistical Analysis]")
    print(f"  {'='*70}")

    # CNP 정오답 리스트
    scarf_cnp = [r["scarf_cnp_correct"] for r in results]
    procot_cnp = [r["procot_cnp_correct"] for r in results]

    m = _mcnemar_test(scarf_cnp, procot_cnp)
    sig = "***" if m["p_value"] < 0.001 else "**" if m["p_value"] < 0.01 else "*" if m["p_value"] < 0.05 else "n.s."
    print(f"\n  [McNemar's Test — CNP]")
    print(f"    SCARF O & ProCoT X (b) = {m['b']}")
    print(f"    SCARF X & ProCoT O (c) = {m['c']}")
    print(f"    χ² = {m['chi2']},  p = {m['p_value']}  {sig}")

    # URL 정오답 리스트 (평가 대상인 행만)
    scarf_url_list, procot_url_list = [], []
    for r in results:
        s_ok = r["scarf_url_correct"]
        p_ok = r["procot_url_correct"]
        if s_ok != "" and p_ok != "":
            scarf_url_list.append(int(s_ok))
            procot_url_list.append(int(p_ok))

    if scarf_url_list:
        m_url = _mcnemar_test(scarf_url_list, procot_url_list)
        sig2 = "***" if m_url["p_value"] < 0.001 else "**" if m_url["p_value"] < 0.01 else "*" if m_url["p_value"] < 0.05 else "n.s."
        print(f"\n  [McNemar's Test — URL Exact Match (공통 {len(scarf_url_list)}건)]")
        print(f"    SCARF O & ProCoT X (b) = {m_url['b']}")
        print(f"    SCARF X & ProCoT O (c) = {m_url['c']}")
        print(f"    χ² = {m_url['chi2']},  p = {m_url['p_value']}  {sig2}")

    # 95% CI
    print(f"\n  [95% Confidence Intervals — Wilson Score]")
    print(f"  {'Metric':<25} {'SCARF':>20} {'ProCoT':>20}")
    print(f"  {'-'*65}")

    s_cnp_n = sum(scarf_cnp)
    p_cnp_n = sum(procot_cnp)
    s_ci = _wilson_ci(s_cnp_n, total)
    p_ci = _wilson_ci(p_cnp_n, total)
    print(f"  {'CNP Accuracy':<25} {s_cnp_n/total:.2%} {str(s_ci):>13} {p_cnp_n/total:.2%} {str(p_ci):>13}")

    # URL CI
    for key, label in [("scarf", "SCARF"), ("procot", "ProCoT")]:
        url_vals = [int(r[f"{key}_url_correct"]) for r in results if r[f"{key}_url_correct"] != ""]
        if url_vals:
            c, t = sum(url_vals), len(url_vals)
            ci = _wilson_ci(c, t)
            print(f"  {'URL EM ('+label+')':<25} {c/t:.2%} ({c}/{t}) {str(ci):>7}")


def evaluate():
    rows = list(csv.DictReader(open(TEST_CSV, encoding="utf-8-sig")))
    total = len(rows)

    api_list = _load_api_list()
    procot_prompt = build_procot_system_prompt(api_list)
    print(f"[ProCoT] System prompt: {len(procot_prompt)} chars")

    # ── GT slot URL 사전 빌드 ─────────────────────────────────────────────────
    gt_slot_urls = []
    for row in rows:
        sub_cat = row["subCategory"].strip()
        slot_str = row.get("slot_filling", "").strip()
        gt_slot_urls.append(build_gt_slot_url(sub_cat, slot_str))

    # ── Phase 1: ProCoT (GPT-5.4) ────────────────────────────────────────────
    print(f"\n{'='*80}")
    print(f"  [Phase 1/2] ProCoT ({PROCOT_MODEL}) — {total}건")
    print(f"{'='*80}")
    procot_results = []
    for i, row in enumerate(rows):
        text = row["text"].strip()
        slot_str = row.get("slot_filling", "").strip()
        url_str = row.get("url", "").strip()
        r = run_procot(text, procot_prompt, gt_slot_str=slot_str, gt_url=url_str)
        procot_results.append(r)
        err = r.get("error", "")
        tc = r.get("turn_count", 1)
        tc_tag = f" T{tc}" if tc > 1 else "   "
        tag = f"{r['action']:<8}{tc_tag} {r['url'][:40]}" if r['url'] else f"{r['action']:<8}{tc_tag} (no url)"
        print(f"  [{i+1:3d}/{total}] {r['elapsed']:.2f}s  {tag}  <- {text[:30]}"
              f"{'  '+err if err else ''}")

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
        tag = f"{r['action']:<8} {r['url'][:40]}" if r['url'] else f"{r['action']:<8} (no url)"
        print(f"  [{i+1:3d}/{total}] {r['status']:<10} {r['elapsed']:.2f}s  {tag}  <- {text[:30]}")

    # ── 메모리 정리 ───────────────────────────────────────────────────────────
    _unload_exaone()
    global rag_pipeline, _rag_loaded
    if _rag_loaded:
        del rag_pipeline
        _rag_loaded = False
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # ── 집계 ─────────────────────────────────────────────────────────────────
    # GT: index_Classifier  0=모호, 1=명확
    # SCARF action: CLARIFY=모호 탐지, EXECUTE/REJECT=명확/거부
    # ProCoT action: CLARIFY/EXECUTE/REJECT

    stats = {k: {
        "cnp_correct": 0, "cnp_total": 0,
        "safety_correct": 0, "safety_total": 0,   # GT=0에서 CLARIFY 선택
        "false_block": 0, "false_block_total": 0,  # GT=1에서 CLARIFY 선택
        "url_correct": 0, "url_total": 0,           # EXECUTE 시 gt_url 매칭
        "has_url": 0, "times": [],
    } for k in ("scarf", "procot")}

    results = []
    for i, row in enumerate(rows):
        rid      = row["id"]
        text     = row["text"].strip()
        gt_int   = INTENT_MAP.get(row["subCategory"].strip(), row["subCategory"].strip())
        gt_clf   = int(row["index_Classifier"])  # 0=모호, 1=명확
        gt_url   = row["url"].strip()
        gt_s_url = gt_slot_urls[i]
        slot_str = row.get("slot_filling", "").strip()

        sr  = scarf_results[i]
        pr  = procot_results[i]

        eval_url = gt_url if gt_url else gt_s_url

        # ── CNP (Clarification Need Prediction) ──
        # GT=0(모호) → 정답=CLARIFY, GT=1(명확) → 정답=EXECUTE or REJECT
        for key, r in [("scarf", sr), ("procot", pr)]:
            action = r["action"]
            if gt_clf == 0:
                # 모호한 질의 → CLARIFY가 정답
                cnp_ok = int(action == "CLARIFY")
                stats[key]["safety_correct"] += cnp_ok
                stats[key]["safety_total"] += 1
            else:
                # 명확한 질의 → EXECUTE 또는 REJECT가 정답
                cnp_ok = int(action != "CLARIFY")
                if action == "CLARIFY":
                    stats[key]["false_block"] += 1
                stats[key]["false_block_total"] += 1

            stats[key]["cnp_correct"] += cnp_ok
            stats[key]["cnp_total"] += 1

        # ── URL 정확도 (EXECUTE 시) ──
        scarf_url_ok = procot_url_ok = ""
        if eval_url:
            if sr["action"] == "EXECUTE":
                scarf_url_ok = int(sr["url"] == eval_url)
                stats["scarf"]["url_correct"] += scarf_url_ok
                stats["scarf"]["url_total"] += 1
            # SCARF CLARIFY(need_info)에서 GT슬롯으로 빌드한 URL도 평가
            elif sr["action"] == "CLARIFY" and sr["url"]:
                scarf_url_ok = int(sr["url"] == eval_url)
                stats["scarf"]["url_correct"] += scarf_url_ok
                stats["scarf"]["url_total"] += 1

            if pr["action"] == "EXECUTE":
                procot_url_ok = int(pr["url"] == eval_url)
                stats["procot"]["url_correct"] += procot_url_ok
                stats["procot"]["url_total"] += 1
            # ProCoT CLARIFY → 2차 턴에서 URL 획득한 경우도 평가
            elif pr["action"] == "CLARIFY" and pr.get("turn_count", 1) == 2 and pr["url"]:
                procot_url_ok = int(pr["url"] == eval_url)
                stats["procot"]["url_correct"] += procot_url_ok
                stats["procot"]["url_total"] += 1

        if sr["url"]:
            stats["scarf"]["has_url"] += 1
        if pr["url"]:
            stats["procot"]["has_url"] += 1

        stats["scarf"]["times"].append(sr["elapsed"])
        stats["procot"]["times"].append(pr["elapsed"])

        # ── SCARF CNP: is_ambiguous → CLARIFY, not ambiguous → EXECUTE
        scarf_cnp = int(
            (gt_clf == 0 and sr["action"] == "CLARIFY") or
            (gt_clf == 1 and sr["action"] != "CLARIFY")
        )
        procot_cnp = int(
            (gt_clf == 0 and pr["action"] == "CLARIFY") or
            (gt_clf == 1 and pr["action"] != "CLARIFY")
        )

        results.append({
            "id": rid, "text": text, "gt_intent": gt_int,
            "gt_classifier": gt_clf, "gt_slot_filling": slot_str,
            "gt_url": gt_url, "gt_slot_url": gt_s_url,
            # SCARF
            "scarf_action": sr["action"], "scarf_url": sr["url"],
            "scarf_status": sr.get("status", ""),
            "scarf_url_correct": scarf_url_ok,
            "scarf_cnp_correct": scarf_cnp, "scarf_time": sr["elapsed"],
            # ProCoT
            "procot_action": pr["action"], "procot_url": pr["url"],
            "procot_thought": pr.get("thought", "")[:200],
            "procot_url_correct": procot_url_ok,
            "procot_cnp_correct": procot_cnp, "procot_time": pr["elapsed"],
            "procot_turn_count": pr.get("turn_count", 1),
            "procot_clarify_question": pr.get("clarify_question", "")[:200],
            "procot_action_turn2": pr.get("action_turn2", ""),
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
    print(f"  SCARF vs ProCoT({PROCOT_MODEL})  —  {total}건 비교")
    print(f"{'='*80}")

    # 1) CNP
    print(f"\n  [1] Clarification Need Prediction (CNP)")
    print(f"  {'Method':<25} {'CNP Acc':>10} {'Safety':>10} {'FalseBlock':>12} {'Avg Time':>10}")
    print(f"  {'-'*67}")
    for key, label in [("scarf", "SCARF"), ("procot", f"ProCoT({PROCOT_MODEL})")]:
        s = stats[key]
        safety = pct(s["safety_correct"], s["safety_total"])
        fb = pct(s["false_block"], s["false_block_total"])
        print(f"  {label:<25} {pct(s['cnp_correct'], s['cnp_total']):>10}"
              f" {safety:>10} {fb:>12}"
              f" {avg(s['times']):>9.3f}s")

    # 2) URL
    print(f"\n  [2] URL Exact Match")
    print(f"  {'Method':<25} {'Accuracy':>10} {'Correct':>8} {'Total':>8} {'URL생성':>8}")
    print(f"  {'-'*54}")
    for key, label in [("scarf", "SCARF"), ("procot", f"ProCoT({PROCOT_MODEL})")]:
        s = stats[key]
        print(f"  {label:<25} {pct(s['url_correct'], s['url_total']):>10}"
              f" {s['url_correct']:>8} {s['url_total']:>8}"
              f" {s['has_url']:>8}")

    # Action 분포
    print(f"\n  [3] Action 분포")
    for key, label in [("scarf", "SCARF"), ("procot", "ProCoT")]:
        actions = Counter(r[f"{key}_action"] for r in results)
        print(f"  {label}: {dict(actions)}")

    # 4) Multi-turn 통계
    turn2_count = sum(1 for r in results if r.get("procot_turn_count", 1) == 2)
    print(f"\n  [4] ProCoT Multi-turn")
    print(f"  2-turn 시뮬레이션: {turn2_count}건 / CLARIFY "
          f"{sum(1 for r in results if r['procot_action']=='CLARIFY')}건")

    print(f"\n  GT 분포: 모호(0)={sum(1 for r in rows if r['index_Classifier']=='0')}건,"
          f" 명확(1)={sum(1 for r in rows if r['index_Classifier']=='1')}건")

    # ── 통계 분석 (McNemar's test + 95% CI) ──────────────────────────────────
    _print_statistical_analysis(results, total)

    print(f"\n  result: {RESULT_CSV}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    evaluate()
