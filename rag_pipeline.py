"""
rag_pipeline.py
ragTest 프레임워크 통합 모듈

파이프라인 흐름:
  1. Retrieval     : classify_command()  → subCategory / mode
  2. Ambiguity     : check_ambiguity()   → is_ambiguous
  3a. 명확한 경우  : LLM 직접 호출 (run_model) → API 실행
  3b. 모호한 경우  : DSTManager 슬롯 필링 → URL 빌드 → API 실행
"""

import sys
import os
import time
from threading import Lock

# ── ragTest 경로 설정 ─────────────────────────────────────────────────────────
RAGTEST_ROOT = r"C:\Users\AMLPC01\Documents\GitHub\ragTest"
RAGTEST_SRC  = os.path.join(RAGTEST_ROOT, "src")
RAGTEST_SLOT = os.path.join(RAGTEST_ROOT, "experiment", "slot_filling")

for _p in [RAGTEST_SRC, RAGTEST_SLOT]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── ragTest 모듈 임포트 ───────────────────────────────────────────────────────
# run_pipeline.py 가 모듈 레벨에서 상대 경로로 파일을 읽으므로,
# 임포트 전에 cwd 를 RAGTEST_SRC 로 변경해야 한다.
_saved_cwd = os.getcwd()
os.chdir(RAGTEST_SRC)

try:
    import run_pipeline                          # SentenceTransformer + 카테고리 설명 로드
    from ambiguity_classifier import classify_ambiguity  # BGE-m3-ko 분류기
    import dst_                                  # DST 슬롯 필링 매니저
finally:
    os.chdir(_saved_cwd)

# ── DST 모델 로드 (절대 경로 사용) ───────────────────────────────────────────
print("[RAG] DST 슬롯 필링 모델 로드 중...")
_DST_CFG = {
    "model_name":     "klue/roberta-base",
    "checkpoint_dir": os.path.join(RAGTEST_SRC, "checkpoints", "slot_filling"),
    "max_length":     128,
}
_dst_model, _dst_tokenizer, _dst_vocab = dst_.load_model(_DST_CFG)
print("[RAG] DST 모델 준비 완료.")

# ── 세션 저장소 ───────────────────────────────────────────────────────────────
SESSION_TTL    = 300   # 5분 (초 단위)
_sessions: dict = {}
_sessions_lock  = Lock()


def _cleanup_sessions() -> None:
    """만료된 세션 삭제 (Lock 내부에서 호출)."""
    now = time.time()
    expired = [k for k, v in _sessions.items() if now - v["created"] > SESSION_TTL]
    for k in expired:
        del _sessions[k]


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────
def _build_url(intent: str, slots: dict) -> str:
    from slot_url_builder import build_url_from_slots
    return build_url_from_slots(intent, slots)


# ── 공개 API ─────────────────────────────────────────────────────────────────
def process_new_query(text: str) -> dict:
    """
    새 사용자 명령에 대해 파이프라인을 실행한다.

    Returns:
        dict with keys:
          - status : "use_llm" | "need_info" | "complete" | "rejected"
          - output : 질문 문자열 (need_info) 또는 API URL (complete)
          - session_id : 세션 ID (need_info 시에만)
          - intent : 분류된 인텐트
          - ambiguity : 모호성 판별 결과 dict
    """
    # Stage 1: 카테고리 분류 (Retrieval)
    sub_category, mode = run_pipeline.classify_command(text)
    print(f"[RAG] Retrieval → sub_category={sub_category}, mode={mode}")

    if mode == "reject":
        return {
            "status":    "rejected",
            "output":    "/NO_FUNCTION",
            "intent":    "no_function",
            "ambiguity": {"is_ambiguous": False, "ambiguity_score": 0.0, "confidence": "rejected"},
        }

    intent = sub_category[0] if isinstance(sub_category, list) else sub_category

    # Stage 2: 모호성 판별
    ambiguity = run_pipeline.check_ambiguity(text, sub_category)
    print(f"[RAG] Ambiguity → {ambiguity}")

    if not ambiguity["is_ambiguous"]:
        # 명확한 명령 → LLM 으로 처리
        return {
            "status":    "use_llm",
            "intent":    intent,
            "ambiguity": ambiguity,
        }

    # Stage 3: 슬롯 필링 시작
    manager = dst_.DSTManager(_dst_model, _dst_tokenizer, _dst_vocab, _DST_CFG)
    state, question = manager.process_first_utterance(text, intent)
    print(f"[RAG] DST first → complete={state.complete}, pending={state.pending}")

    if state.complete:
        url = _build_url(intent, state.slots)
        return {
            "status":    "complete",
            "output":    url,
            "intent":    intent,
            "slots":     state.slots,
            "ambiguity": ambiguity,
        }

    # 슬롯이 아직 비어 있음 → 세션 저장 후 첫 질문 반환
    session_id = state.turn_id
    with _sessions_lock:
        _cleanup_sessions()
        _sessions[session_id] = {
            "manager": manager,
            "intent":  intent,
            "created": time.time(),
        }

    return {
        "status":     "need_info",
        "output":     question,
        "session_id": session_id,
        "intent":     intent,
        "ambiguity":  ambiguity,
    }


def continue_session(session_id: str, answer: str) -> dict:
    """
    슬롯 필링 세션에 사용자 답변을 전달한다.

    Returns:
        dict with keys:
          - status : "need_info" | "complete" | "error"
          - output : 다음 질문 (need_info) 또는 API URL (complete) 또는 오류 메시지
          - session_id : (need_info 시에만)
          - intent : 인텐트
          - slots  : (complete 시에만) 채워진 슬롯 dict
    """
    with _sessions_lock:
        session = _sessions.get(session_id)

    if not session:
        return {
            "status": "error",
            "output": "세션이 만료되었습니다. 새 명령을 입력해주세요.",
        }

    manager = session["manager"]
    intent  = session["intent"]

    state, question = manager.process_answer(answer)
    print(f"[RAG] DST answer → complete={state.complete}, pending={state.pending}, slots={state.slots}")

    if state.complete or not question:
        with _sessions_lock:
            _sessions.pop(session_id, None)
        url = _build_url(intent, state.slots)
        return {
            "status": "complete",
            "output": url,
            "intent": intent,
            "slots":  state.slots,
        }

    return {
        "status":     "need_info",
        "output":     question,
        "session_id": session_id,
        "intent":     intent,
    }
