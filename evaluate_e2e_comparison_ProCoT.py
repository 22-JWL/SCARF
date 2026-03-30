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

import csv, json, time, os, sys, re
from pathlib import Path
from datetime import datetime
from collections import Counter

import numpy as np

# ── 설정 ─────────────────────────────────────────────────────────────────────
TEST_CSV      = "test_queries_labeled_url.csv"
PROCOT_MODEL  = "gpt-5.4"
MAX_PROCOT_TURNS = 10  # SCARF slot filling과 동등한 최대 턴 수

OUTPUT_DIR = Path("eval_results")
OUTPUT_DIR.mkdir(exist_ok=True)
TIMESTAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
RESULT_CSV = OUTPUT_DIR / f"eval_procot_{TIMESTAMP}.csv"

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
    "roi_type": "{v} ROI 타입",
    "roi_action": "ROI {v}",
    "filter_type": "{v} 필터",
    "date_range": "기간은 {v}",
    "camera_type": "{v} 카메라",
    "history_inspection_type": "{v} 검사 유형",
    "option_type": "{v} 옵션",
    "option_value": "{v}으로 설정",
    "parameter_name": "{v} 파라미터",
    "parameter_value": "값은 {v}",
    "size_type": "{v} 사이즈",
    "size_value": "크기는 {v}",
    "geometry_position": "{v} 위치",
    "coordinate_value": "좌표 {v}",
    "recipe_name": "{v} 레시피",
    "target_name": "{v} 타겟",
    "action_type": "{v} 동작",
    "button_action": "{v}",
    "shape_type": "{v} 모양",
    "similarity_value": "유사도 {v}",
    "reference_type": "{v} 기준",
    "reticle_type": "십자선 {v}",
    "tab_name": "{v} 탭으로",
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


def _build_slot_answer_queue(slot_str: str, gt_url: str = "") -> list:
    """
    GT 슬롯을 개별 자연어 응답 리스트로 변환.
    SCARF의 per-slot 질의와 동등한 정보량을 턴당 하나씩 제공.
    """
    if not slot_str or slot_str.strip() == "NONE":
        return []

    all_slots = {}
    for pair in slot_str.strip().split("|"):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        all_slots[k.strip()] = v.strip()

    if not all_slots:
        return []

    # gt_url에서 파라미터 추출
    url_params = {}
    if gt_url and "?" in gt_url:
        param_str = gt_url.split("?", 1)[1]
        for p in param_str.split("&"):
            if "=" in p:
                pk, pv = p.split("=", 1)
                url_params[pk.strip()] = pv.strip()

    # NONE 슬롯에 기본값 채우기
    for k, v in list(all_slots.items()):
        if v == "NONE":
            if k == "window_name" and gt_url:
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
            all_slots[k] = _SLOT_DEFAULTS.get(k, "default")

    # 개별 슬롯 답변 생성
    answers = []
    for k, v in all_slots.items():
        template = _SLOT_LABELS.get(k, "{v}")
        answers.append(template.format(v=v))

    return answers


def run_procot(text: str, system_prompt: str, gt_slot_str: str = "",
               gt_url: str = "") -> dict:
    """
    ProCoT prompting으로 GPT-5.4 호출.
    CLARIFY 시 GT 슬롯 기반 progressive mock answer로 최대 MAX_PROCOT_TURNS턴 시뮬레이션.
    (SCARF의 slot filling 멀티턴과 동등한 정보 예산)

    Returns:
        first_action : 1차 판정 (CNP 평가용)
        action       : 최종 판정 (URL 평가용)
        url          : 최종 URL
    """
    key = _get_openai_key()
    if not key:
        return {"thought": "", "action": "", "first_action": "", "response": "",
                "url": "", "elapsed": 0.0, "clarify_questions": [],
                "turn_count": 0, "error": "OPENAI_API_KEY not set"}

    from openai import OpenAI
    client = OpenAI(api_key=key)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": text},
    ]

    # 슬롯별 progressive mock answer 큐
    answer_queue = _build_slot_answer_queue(gt_slot_str, gt_url=gt_url)
    # fallback: 전체 mock answer (큐 소진 후 사용)
    full_mock = _build_mock_answer(gt_slot_str, gt_url=gt_url)

    t0 = time.time()
    clarify_questions = []
    turn_count = 1
    answer_idx = 0
    first_action = ""

    try:
        # ── 1차 호출 ──
        resp = client.chat.completions.create(
            model=PROCOT_MODEL, messages=messages,
            temperature=0, max_completion_tokens=500,
        )
        raw = resp.choices[0].message.content.strip()
        parsed = parse_procot_response(raw)
        first_action = parsed["action"]

        # ── 멀티턴 루프: CLARIFY → mock answer → 재호출 (최대 MAX_PROCOT_TURNS) ──
        while parsed["action"] == "CLARIFY" and turn_count < MAX_PROCOT_TURNS:
            # mock answer 선택: 큐에서 순서대로 → 소진 시 전체 답변
            if answer_idx < len(answer_queue):
                mock = answer_queue[answer_idx]
                answer_idx += 1
            elif full_mock:
                mock = full_mock
                full_mock = ""  # 전체 답변도 1회만 사용
            else:
                break  # 제공할 정보 없음

            clarify_questions.append(parsed["response"])
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": mock})

            resp = client.chat.completions.create(
                model=PROCOT_MODEL, messages=messages,
                temperature=0, max_completion_tokens=500,
            )
            raw = resp.choices[0].message.content.strip()
            parsed = parse_procot_response(raw)
            turn_count += 1

    except Exception as e:
        raw = f"ERROR: {e}"
        parsed = {"thought": "", "action": "ERROR", "response": str(e),
                  "url": "", "error": str(e)[:100]}

    elapsed = round(time.time() - t0, 4)
    parsed["first_action"] = first_action
    parsed["elapsed"] = elapsed
    parsed["clarify_questions"] = clarify_questions
    parsed["turn_count"] = turn_count
    parsed["raw"] = raw
    return parsed


# ── 5. 평가 메인 ────────────────────────────────────────────────────────────


def _wilson_ci(correct: int, total: int, z: float = 1.96) -> tuple:
    """Wilson score 95% confidence interval for a proportion."""
    if total == 0:
        return (0.0, 0.0)
    p = correct / total
    denom = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    spread = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denom
    return (round(max(0, center - spread), 4), round(min(1, center + spread), 4))


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

    # ── ProCoT (GPT-5.4) — 멀티턴 (최대 {MAX_PROCOT_TURNS}턴) ─────────────────
    print(f"\n{'='*80}")
    print(f"  ProCoT ({PROCOT_MODEL}) — {total}건  (max {MAX_PROCOT_TURNS} turns)")
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
        first_a = r.get("first_action", r["action"])
        final_a = r["action"]
        action_tag = f"{first_a}>{final_a}" if first_a != final_a else first_a
        tc_tag = f" T{tc}" if tc > 1 else "   "
        tag = f"{action_tag:<17}{tc_tag} {r['url'][:40]}" if r['url'] else f"{action_tag:<17}{tc_tag} (no url)"
        print(f"  [{i+1:3d}/{total}] {r['elapsed']:.2f}s  {tag}  <- {text[:30]}"
              f"{'  '+err if err else ''}")

    # ── 집계 ─────────────────────────────────────────────────────────────────
    # CNP는 first_action(1차 판정)으로, URL은 최종 action으로 평가
    stats = {
        "cnp_correct": 0, "cnp_total": 0,
        "safety_correct": 0, "safety_total": 0,
        "false_block": 0, "false_block_total": 0,
        "url_correct": 0, "url_total": 0,
        "has_url": 0, "times": [],
        "turn_counts": [],
    }

    results = []
    for i, row in enumerate(rows):
        rid      = row["id"]
        text     = row["text"].strip()
        gt_int   = INTENT_MAP.get(row["subCategory"].strip(), row["subCategory"].strip())
        gt_clf   = int(row["index_Classifier"])  # 0=모호, 1=명확
        gt_url   = row["url"].strip()
        gt_s_url = gt_slot_urls[i]
        slot_str = row.get("slot_filling", "").strip()

        pr  = procot_results[i]
        eval_url = gt_url if gt_url else gt_s_url

        # ── CNP: first_action(1차 판정) 기준 ──
        first_action = pr.get("first_action", pr["action"])
        if gt_clf == 0:
            cnp_ok = int(first_action == "CLARIFY")
            stats["safety_correct"] += cnp_ok
            stats["safety_total"] += 1
        else:
            cnp_ok = int(first_action != "CLARIFY")
            if first_action == "CLARIFY":
                stats["false_block"] += 1
            stats["false_block_total"] += 1
        stats["cnp_correct"] += cnp_ok
        stats["cnp_total"] += 1

        # ── URL 정확도: 최종 action 기준, 미생성 = 오답 ──
        procot_url_ok = ""
        if eval_url:
            if pr["url"]:
                procot_url_ok = int(pr["url"] == eval_url)
            else:
                procot_url_ok = 0  # URL 미생성 = 오답 (SCARF와 동일 모수)
            stats["url_correct"] += procot_url_ok
            stats["url_total"] += 1

        if pr["url"]:
            stats["has_url"] += 1
        stats["times"].append(pr["elapsed"])
        stats["turn_counts"].append(pr.get("turn_count", 1))

        procot_cnp = int(
            (gt_clf == 0 and first_action == "CLARIFY") or
            (gt_clf == 1 and first_action != "CLARIFY")
        )

        results.append({
            "id": rid, "text": text, "gt_intent": gt_int,
            "gt_classifier": gt_clf, "gt_slot_filling": slot_str,
            "gt_url": gt_url, "gt_slot_url": gt_s_url,
            # ProCoT
            "procot_first_action": first_action,
            "procot_final_action": pr["action"],
            "procot_url": pr["url"],
            "procot_thought": pr.get("thought", "")[:200],
            "procot_url_correct": procot_url_ok,
            "procot_cnp_correct": procot_cnp,
            "procot_time": pr["elapsed"],
            "procot_turn_count": pr.get("turn_count", 1),
            "procot_clarify_questions": "; ".join(pr.get("clarify_questions", []))[:300],
        })

    # ── CSV 저장 ─────────────────────────────────────────────────────────────
    procot_fieldnames = [
        "id", "text", "gt_intent", "gt_classifier", "gt_slot_filling", "gt_url", "gt_slot_url",
        "procot_first_action", "procot_final_action", "procot_url", "procot_thought",
        "procot_url_correct", "procot_cnp_correct", "procot_time",
        "procot_turn_count", "procot_clarify_questions",
    ]
    with open(RESULT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=procot_fieldnames)
        w.writeheader()
        w.writerows(results)

    # ── 요약 출력 ────────────────────────────────────────────────────────────
    def pct(a, b): return f"{a/b:.2%}" if b else "N/A"
    def avg(lst): return round(sum(lst)/len(lst), 4) if lst else 0.0

    s = stats
    print(f"\n{'='*80}")
    print(f"  ProCoT({PROCOT_MODEL}) 단독 평가  —  {total}건  (max {MAX_PROCOT_TURNS} turns)")
    print(f"{'='*80}")

    # 1) CNP (1차 판정 기준)
    print(f"\n  [1] Clarification Need Prediction (CNP) — 1차 판정 기준")
    print(f"  {'Metric':<25} {'Value':>10}")
    print(f"  {'-'*35}")
    print(f"  {'CNP Accuracy':<25} {pct(s['cnp_correct'], s['cnp_total']):>10}")
    print(f"  {'Safety Rate':<25} {pct(s['safety_correct'], s['safety_total']):>10}")
    print(f"  {'False Block Rate':<25} {pct(s['false_block'], s['false_block_total']):>10}")
    print(f"  {'Avg Latency':<25} {avg(s['times']):>9.3f}s")

    # 2) URL (멀티턴 최종 결과 기준, 미생성=오답)
    print(f"\n  [2] URL Exact Match — 멀티턴 최종 결과 (미생성=오답)")
    print(f"  {'Metric':<25} {'Value':>10}")
    print(f"  {'-'*35}")
    print(f"  {'Accuracy':<25} {pct(s['url_correct'], s['url_total']):>10}")
    print(f"  {'Correct':<25} {s['url_correct']:>10}")
    print(f"  {'Total (evaluated)':<25} {s['url_total']:>10}")
    print(f"  {'URL 생성 건수':<25} {s['has_url']:>10}")
    no_url = s['url_total'] - s['has_url']
    if no_url > 0:
        print(f"  {'URL 미생성 (=오답)':<25} {no_url:>10}")

    # 3) Action 분포
    print(f"\n  [3] Action 분포")
    first_actions = Counter(r["procot_first_action"] for r in results)
    final_actions = Counter(r["procot_final_action"] for r in results)
    print(f"  1차 판정: {dict(first_actions)}")
    print(f"  최종:     {dict(final_actions)}")

    # 4) Multi-turn 통계
    tc_list = s["turn_counts"]
    tc_dist = Counter(tc_list)
    print(f"\n  [4] Multi-turn 통계")
    print(f"  평균 턴 수: {avg(tc_list):.2f}")
    for t in sorted(tc_dist.keys()):
        print(f"    {t}턴: {tc_dist[t]}건")

    print(f"\n  GT 분포: 모호(0)={sum(1 for r in rows if r['index_Classifier']=='0')}건,"
          f" 명확(1)={sum(1 for r in rows if r['index_Classifier']=='1')}건")

    # ── 95% CI ────────────────────────────────────────────────────────────────
    print(f"\n  [95% Confidence Intervals — Wilson Score]")
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
