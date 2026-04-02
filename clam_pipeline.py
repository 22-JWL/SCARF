"""
clam_pipeline.py
CLAM (Contrastive Learning with Ambiguity Management) 파이프라인

[SCARF와의 차이]
  Stage2 : BGE fine-tuned 분류기    → GPT-5.4 5-shot 프롬프팅으로 대체
  Stage3a: RoBERTa 슬롯 필링        → 없음
  URL 생성: 룰베이스 빌더           → GPT-5.4가 직접 생성

[흐름]
  Step1 : KoE5 retrieve → subCategory + top-k action docs  (SCARF Stage1 재활용)
  Step2 : GPT-5.4 + top-k docs → EXECUTE / CLARIFY / REJECT  (5-shot 프롬프팅)
  Step3a: EXECUTE → GPT-5.4가 URL 직접 생성
  Step3b: CLARIFY → 명확화 Q&A (GT 슬롯 mock answer) → URL 생성
"""

import os
import sys
import re
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# ── RAGTEST 경로 설정 ──────────────────────────────────────────────────────────
# 코드(run_pipeline.py)  : flask_LLM/ragTest/src/  (수정된 버전)
# 체크포인트/데이터/DB    : deepseers/ragTest/src/  (실제 파일 위치)
RAGTEST_CODE_ROOT = PROJECT_ROOT / "ragTest"
RAGTEST_CODE_SRC  = RAGTEST_CODE_ROOT / "src"

RAGTEST_DATA_ROOT = PROJECT_ROOT.parent / "ragTest"   # C:\Users\AMLPC03\deepseers\ragTest
RAGTEST_DATA_SRC  = RAGTEST_DATA_ROOT / "src"         # 체크포인트/chroma_action_db/data

# sys.path: flask_LLM의 run_pipeline.py를 우선 로드
if str(RAGTEST_CODE_SRC) not in sys.path:
    sys.path.insert(0, str(RAGTEST_CODE_SRC))

# cwd: 외부 ragTest/src로 설정 → MODEL_PATH 상대경로가 실제 체크포인트를 가리킴
_saved_cwd = os.getcwd()
os.chdir(str(RAGTEST_DATA_SRC))
try:
    import run_pipeline
    from langchain_huggingface import HuggingFaceEmbeddings
finally:
    os.chdir(_saved_cwd)

# ── Vectorstore 초기화 (최초 1회) ─────────────────────────────────────────────
print("[CLAM] Vectorstore 초기화 중...")
_embeddings = HuggingFaceEmbeddings(
    model_name="nlpai-lab/KoE5",
    model_kwargs={"device": "cpu"},
)
run_pipeline.vectorstore = run_pipeline.load_or_build_vectorstore(
    persist_dir=str(RAGTEST_DATA_SRC / "chroma_action_db"),
    embeddings=_embeddings,
    action_path=str(RAGTEST_DATA_ROOT / "data" / "action.json"),
)
print("[CLAM] Vectorstore 준비 완료.")

CLAM_MODEL      = "gpt-5.4"
MAX_CLAM_TURNS  = 10   # SCARF slot filling과 동등한 최대 턴 수


# ── 시스템 프롬프트 ────────────────────────────────────────────────────────────
def build_clam_system_prompt() -> str:
    """
    CLAM 시스템 프롬프트.
    ProCoT와 동일한 [Thought]/[Action]/[Response] 구조.
    전체 API 목록 대신 검색된 top-k 문서가 user 메시지에 동적으로 주입된다.
    """
    return """너는 반도체 공정 비전 검사(AOI) 장비의 대화형 제어 인터페이스야.
사용자 명령과 함께 **검색된 API 후보 목록**이 제공된다.
아래 3단계를 **반드시 순서대로** 수행해.

## Step 1 - Thought (분석)
- 제공된 API 후보 중 이 명령에 정확히 해당하는 API를 특정할 수 있는가?
- 필수 파라미터(창 이름, 값, 타입 등)가 모두 명시되어 있는가?
- 여러 API에 해당할 수 있어 모호한가?
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
사용자 명령: "BGA 창에서 Scratch 임계값을 150으로 설정해줘"
검색된 API 후보:
1. [bga] update_threshold - BGA 창 임계값 설정 (ScratchThreshold, PackageThreshold 포함)
```
[Thought] BGA 창, ScratchThreshold, 값 150이 모두 명시됨. 후보 1번으로 특정 가능.
[Action] EXECUTE
[Response] /teaching/bga/update?propertyName=ScratchThreshold&value=150
```

## 예시 2 - 모호한 명령
사용자 명령: "임계값 올려"
검색된 API 후보:
1. [lga] update_threshold - LGA 창 임계값 설정
2. [bga] update_threshold - BGA 창 임계값 설정
3. [qfn] update_threshold - QFN 창 임계값 설정
```
[Thought] 어떤 창인지, 어떤 임계값인지, 몇으로 올릴지 불명확. 여러 후보에 해당.
[Action] CLARIFY
[Response] 어떤 창(lga/bga/qfn 등)에서 어떤 임계값을 몇으로 변경하시겠습니까?
```

## 예시 3 - 관련 없는 질의
사용자 명령: "오늘 점심 뭐 먹지?"
검색된 API 후보:
(없음)
```
[Thought] 장비 제어와 관련 없는 일상 질문.
[Action] REJECT
[Response] /NO_FUNCTION
```
"""


# ── 후보 포맷터 & user 메시지 빌더 ────────────────────────────────────────────
def _format_candidates(candidates: list) -> str:
    if not candidates:
        return "(없음)"
    lines = []
    for i, c in enumerate(candidates, 1):
        window = c.get("windowName", "")
        api    = c.get("api_name", "")
        desc   = c.get("description", "")
        use    = c.get("useCase", "")
        detail = f"{desc} ({use})" if use else desc
        lines.append(f"{i}. [{window}] {api} - {detail}")
    return "\n".join(lines)


def build_user_message(text: str, candidates: list) -> str:
    """발화 + top-k 후보를 합친 user 메시지 (per-query 동적 주입)."""
    return f"사용자 명령: \"{text}\"\n\n검색된 API 후보:\n{_format_candidates(candidates)}"


# ── 응답 파싱 (ProCoT와 동일 구조) ────────────────────────────────────────────
def parse_clam_response(raw: str) -> dict:
    thought = action = response = ""

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

    url = ""
    if action == "EXECUTE":
        api_lines = [l.strip() for l in response.split("\n") if l.strip().startswith("/")]
        url = "\n".join(api_lines) if api_lines else response
    elif action == "REJECT":
        url = "/NO_FUNCTION"

    if not action:
        if "/NO_FUNCTION" in raw:
            action = "REJECT"; url = "/NO_FUNCTION"
        elif any(l.strip().startswith("/") for l in raw.split("\n")):
            action = "EXECUTE"
            api_lines = [l.strip() for l in raw.split("\n") if l.strip().startswith("/")]
            url = "\n".join(api_lines)
        else:
            action = "CLARIFY"

    return {"thought": thought, "action": action, "response": response, "url": url.strip()}


# ── OpenAI key 로드 ────────────────────────────────────────────────────────────
def _get_openai_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    return key


# ── Mock answer 헬퍼 (ProCoT와 동일) ─────────────────────────────────────────
_SLOT_DEFAULTS = {
    "window_name": "bga", "auto_type": "AutoThresholdSet",
    "threshold_value": "150", "threshold_type": "ScratchThreshold",
    "operation": "teaching", "inspection_type": "full",
    "roi_type": "roi", "filter_type": "date", "date_range": "today",
    "camera_type": "top", "option_value": "on",
    "recipe_name": "default", "target_name": "default",
    "coordinate_value": "0", "button_action": "start",
    "shape_type": "circle", "similarity_value": "80",
    "reference_type": "golden", "reticle_type": "standard",
    "history_inspection_type": "all",
}

_SLOT_LABELS = {
    "window_name": "{v} 창에서", "auto_type": "{v} 실행",
    "threshold_value": "값은 {v}으로", "threshold_type": "{v} 항목",
    "operation": "{v} 모드로", "inspection_type": "{v} 검사",
    "roi_type": "{v} ROI 타입", "roi_action": "ROI {v}",
    "filter_type": "{v} 필터", "date_range": "기간은 {v}",
    "camera_type": "{v} 카메라", "history_inspection_type": "{v} 검사 유형",
    "option_type": "{v} 옵션", "option_value": "{v}으로 설정",
    "parameter_name": "{v} 파라미터", "parameter_value": "값은 {v}",
    "size_type": "{v} 사이즈", "size_value": "크기는 {v}",
    "geometry_position": "{v} 위치", "coordinate_value": "좌표 {v}",
    "recipe_name": "{v} 레시피", "target_name": "{v} 타겟",
    "action_type": "{v} 동작", "button_action": "{v}",
    "shape_type": "{v} 모양", "similarity_value": "유사도 {v}",
    "reference_type": "{v} 기준", "reticle_type": "십자선 {v}",
    "tab_name": "{v} 탭으로",
}


def _fill_none_slots(all_slots: dict, gt_url: str) -> dict:
    """NONE 슬롯에 GT URL 파라미터 또는 기본값을 채운다."""
    url_params = {}
    if gt_url and "?" in gt_url:
        for p in gt_url.split("?", 1)[1].split("&"):
            if "=" in p:
                pk, pv = p.split("=", 1)
                url_params[pk.strip()] = pv.strip()

    for k, v in all_slots.items():
        if v != "NONE":
            continue
        if k == "window_name" and gt_url:
            parts = gt_url.split("?")[0].strip("/").split("/")
            if len(parts) >= 2:
                all_slots[k] = parts[1]; continue
        if k == "threshold_value" and "value" in url_params:
            all_slots[k] = url_params["value"]; continue
        if k == "threshold_type" and "propertyName" in url_params:
            all_slots[k] = url_params["propertyName"]; continue
        all_slots[k] = _SLOT_DEFAULTS.get(k, "default")
    return all_slots


def _parse_slot_str(slot_str: str) -> dict:
    if not slot_str or slot_str.strip() == "NONE":
        return {}
    out = {}
    for pair in slot_str.strip().split("|"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _build_mock_answer(slot_str: str, gt_url: str = "") -> str:
    """GT 슬롯 전체를 자연어 1문장으로 변환 (CLARIFY fallback 답변)."""
    slots = _fill_none_slots(_parse_slot_str(slot_str), gt_url)
    if not slots:
        return ""
    parts = [_SLOT_LABELS.get(k, "{v}").format(v=v) for k, v in slots.items()]
    return ", ".join(parts)


def _build_slot_answer_queue(slot_str: str, gt_url: str = "") -> list:
    """GT 슬롯을 슬롯별 자연어 답변 리스트로 변환 (턴당 하나씩 제공)."""
    slots = _fill_none_slots(_parse_slot_str(slot_str), gt_url)
    if not slots:
        return []
    return [_SLOT_LABELS.get(k, "{v}").format(v=v) for k, v in slots.items()]


# ── 메인 실행 함수 ─────────────────────────────────────────────────────────────
def run_clam(text: str, system_prompt: str, gt_slot_str: str = "",
             gt_url: str = "") -> dict:
    """
    CLAM 파이프라인 실행.

    Step1 : KoE5 Stage1 retriever → subCategory + top-k action docs
    Step2~4: GPT-5.4 + top-k docs → EXECUTE/CLARIFY/REJECT → URL (멀티턴)

    Args:
        text         : 사용자 발화
        system_prompt: build_clam_system_prompt() 결과
        gt_slot_str  : GT slot_filling (평가용 mock answer 생성에 사용)
        gt_url       : GT url (NONE 슬롯 보완에 사용)

    Returns:
        first_action    : 1차 판정 (CNP 평가용)
        action          : 최종 판정
        url             : 최종 URL
        thought         : LLM Thought 내용
        elapsed         : 총 소요시간(초)
        turn_count      : 실제 턴 수
        clarify_questions: CLARIFY 시 생성된 질문 목록
        sub_category    : Stage1 분류 결과
    """
    key = _get_openai_key()
    if not key:
        return {
            "thought": "", "action": "", "first_action": "", "response": "",
            "url": "", "elapsed": 0.0, "clarify_questions": [],
            "turn_count": 0, "sub_category": "", "error": "OPENAI_API_KEY not set",
        }

    from openai import OpenAI
    client = OpenAI(api_key=key)

    t0 = time.time()

    # ── Step 1: KoE5 Stage1 retriever ────────────────────────────────────────
    sub_category, mode = run_pipeline.classify_command(text)

    if mode == "reject":
        return {
            "thought": "Stage1 reject — 관련 없는 명령",
            "action": "REJECT", "first_action": "REJECT",
            "response": "/NO_FUNCTION", "url": "/NO_FUNCTION",
            "elapsed": round(time.time() - t0, 4),
            "clarify_questions": [], "turn_count": 0,
            "sub_category": "no_function",
        }

    candidates = run_pipeline.retrieve_action(sub_category, text, k=5)

    # ── Step 2~4: GPT-5.4 멀티턴 ─────────────────────────────────────────────
    user_msg = build_user_message(text, candidates)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_msg},
    ]

    answer_queue = _build_slot_answer_queue(gt_slot_str, gt_url=gt_url)
    full_mock    = _build_mock_answer(gt_slot_str, gt_url=gt_url)

    clarify_questions = []
    turn_count  = 1
    answer_idx  = 0
    first_action = ""

    try:
        resp = client.chat.completions.create(
            model=CLAM_MODEL, messages=messages,
            temperature=0, max_completion_tokens=500,
        )
        raw    = resp.choices[0].message.content.strip()
        parsed = parse_clam_response(raw)
        first_action = parsed["action"]

        while parsed["action"] == "CLARIFY" and turn_count < MAX_CLAM_TURNS:
            if answer_idx < len(answer_queue):
                mock = answer_queue[answer_idx]; answer_idx += 1
            elif full_mock:
                mock = full_mock; full_mock = ""
            else:
                break

            clarify_questions.append(parsed["response"])
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user",      "content": mock})

            resp = client.chat.completions.create(
                model=CLAM_MODEL, messages=messages,
                temperature=0, max_completion_tokens=500,
            )
            raw    = resp.choices[0].message.content.strip()
            parsed = parse_clam_response(raw)
            turn_count += 1

    except Exception as e:
        raw    = f"ERROR: {e}"
        parsed = {"thought": "", "action": "ERROR", "response": str(e),
                  "url": "", "error": str(e)[:100]}

    parsed["first_action"]     = first_action
    parsed["elapsed"]          = round(time.time() - t0, 4)
    parsed["clarify_questions"] = clarify_questions
    parsed["turn_count"]       = turn_count
    parsed["raw"]              = raw
    parsed["sub_category"]     = (
        sub_category if isinstance(sub_category, str) else sub_category[0]
    )
    return parsed
