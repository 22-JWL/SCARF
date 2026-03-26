"""
rag_pipeline.py
SCARF (Stage-wise Clarification-based Ambiguity-Resolving Framework) 통합 모듈

파이프라인 흐름:
  Stage 1. Concept-level Retriever
           classify_command(text) → subCategory + mode
  Stage 2. Neural Relevance Scoring  ← action.json 사용
           retrieve_action(subCategory, text) → API 후보 목록
           classify_ambiguity(text, top_action_description) → is_ambiguous
           ※ "이 명령이 특정 API를 지목하기에 충분히 명확한가?"를 판단
  Stage 3a. 명확한 경우 → LLM(run_model) → API 실행
  Stage 3b. 모호한 경우 → DSTManager 슬롯 필링 → URL 빌드 → API 실행
"""

import sys
import os
import time
from threading import Lock

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
RAGTEST_ROOT = r"C:\Users\AMLPC01\PycharmProjects\flask_LLM\ragTest"
# os.path.join(os.path.dirname(os.path.abspath(__file__)), "ragTest")
RAGTEST_SRC  = os.path.join(RAGTEST_ROOT, "src")
RAGTEST_SLOT = os.path.join(RAGTEST_ROOT, "experiment", "slot_filling")

for _p in [RAGTEST_SRC, RAGTEST_SLOT]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

_saved_cwd = os.getcwd()
os.chdir(RAGTEST_SRC)

try:
    import run_pipeline
    from ambiguity_classifier import classify_ambiguity
    import dst_
    from langchain_huggingface import HuggingFaceEmbeddings
finally:
    os.chdir(_saved_cwd)

print("[RAG] Vectorstore 초기화 중 (action.json 로드)...")
_embeddings = HuggingFaceEmbeddings(
    model_name="nlpai-lab/KoE5",
    model_kwargs={"device": "cpu"},
)
run_pipeline.vectorstore = run_pipeline.load_or_build_vectorstore(
    persist_dir=os.path.join(RAGTEST_SRC, "chroma_action_db"),
    embeddings=_embeddings,
    action_path=os.path.join(RAGTEST_ROOT, "data", "action.json"),
)
print("[RAG] Vectorstore 준비 완료.")

print("[RAG] DST 슬롯 필링 모델 로드 중...")
_DST_CFG = {
    "model_name":     "klue/roberta-base",
    "checkpoint_dir": os.path.join(RAGTEST_SRC, "checkpoints", "slot_filling"),
    "max_length":     128,
}
_dst_model, _dst_tokenizer, _dst_vocab = dst_.load_model(_DST_CFG)
print("[RAG] DST 모델 준비 완료.")

SESSION_TTL   = 300
_sessions: dict = {}
_sessions_lock  = Lock()


def _cleanup_sessions() -> None:
    now = time.time()
    expired = [k for k, v in _sessions.items() if now - v["created"] > SESSION_TTL]
    for k in expired:
        del _sessions[k]


def _build_url(intent: str, slots: dict) -> str:
    from slot_url_builder import build_url_from_slots
    return build_url_from_slots(intent, slots)


def _make_action_document(candidates: list, score_gap_threshold: float = 0.05) -> str:
    """
    top-1과 score 차이가 threshold 이내인 후보들을 모두 포함하여
    ambiguity classifier에 전달할 document 문자열을 생성한다.
    차이가 크면 top-1만, 작으면 top-3까지 포함하여 모호성 판단 정확도를 높인다.
    """
    if not candidates:
        return ""

    # Chroma는 distance 반환 (낮을수록 좋음) → gap = c.score - top_score
    top_score = candidates[0].get("score", 0)
    close = [c for c in candidates
             if c.get("score", 0) - top_score <= score_gap_threshold]
    close = close[:3]

    parts = []
    for c in close:
        desc = c.get("description", "")
        use  = c.get("useCase", "")
        entry = f"{desc} ({use})" if use else desc
        if entry:
            parts.append(entry)
    # 학습 데이터와 동일하게 newline 구분
    return "\n".join(parts)


def process_new_query(text: str) -> dict:
    """
    새 사용자 명령에 대해 SCARF 파이프라인을 실행한다.

    Returns dict:
      status     : "use_llm" | "need_info" | "complete" | "rejected"
      output     : API URL(complete) 또는 슬롯 필링 질문(need_info)
      session_id : need_info 일 때만
      intent     : 분류된 인텐트
      slots      : 현재 DST 상태
      ambiguity  : 모호성 판별 결과
      stage_times: 각 스텝 소요시간(초)
    """
    # ── Stage 1 ───────────────────────────────────────────────────────────────
    t0 = time.time()
    sub_category, mode = run_pipeline.classify_command(text)
    t_retriever = round(time.time() - t0, 4)
    print(f"[RAG Stage1] sub_category={sub_category}, mode={mode}")

    if mode == "reject":
        return {
            "status":    "rejected",
            "output":    "/NO_FUNCTION",
            "intent":    "no_function",
            "ambiguity": {"is_ambiguous": False, "ambiguity_score": 0.0, "confidence": "rejected"},
            "stage_times": {"retriever_s": t_retriever, "classifier_s": 0.0, "slot_s": 0.0, "exaone_s": 0.0},
        }

    intent = sub_category[0] if isinstance(sub_category, list) else sub_category

    # ── Stage 2 ───────────────────────────────────────────────────────────────
    t0 = time.time()
    action_candidates = run_pipeline.retrieve_action(sub_category, text, k=5)
    print(f"[RAG Stage2a] top action: {action_candidates[0] if action_candidates else 'none'}")

    if action_candidates:
        action_doc = _make_action_document(action_candidates)
        ambiguity  = classify_ambiguity(text, action_doc)
    else:
        ambiguity = run_pipeline.check_ambiguity(text, sub_category)
    t_classifier = round(time.time() - t0, 4)
    print(f"[RAG Stage2b] ambiguity={ambiguity}")

    # 명확 → LLM  # 일단 슬롯 평가를 위해 주석 처리
    if not ambiguity["is_ambiguous"]:
        return {
            "status":    "use_llm",
            "intent":    intent,
            "ambiguity": ambiguity,
            "stage_times": {"retriever_s": t_retriever, "classifier_s": t_classifier, "slot_s": 0.0, "exaone_s": 0.0},
        }

    # ── Stage 3b: 모호 → 슬롯 필링 ───────────────────────────────────────────
    t0 = time.time()
    manager = dst_.DSTManager(_dst_model, _dst_tokenizer, _dst_vocab, _DST_CFG)
    state, question = manager.process_first_utterance(text, intent)
    t_slot = round(time.time() - t0, 4)
    print(f"[RAG Stage3b] complete={state.complete}, pending={state.pending}")

    stage_times = {"retriever_s": t_retriever, "classifier_s": t_classifier, "slot_s": t_slot, "exaone_s": 0.0}

    if state.complete:
        url = _build_url(intent, state.slots)
        return {
            "status":    "complete",
            "output":    url,
            "intent":    intent,
            "slots":     dict(state.slots),
            "ambiguity": ambiguity,
            "stage_times": stage_times,
        }

    session_id = state.turn_id
    with _sessions_lock:
        _cleanup_sessions()
        _sessions[session_id] = {
            "manager": manager,
            "intent":  intent,
            "created": time.time(),
        }

    return {
        "status":      "need_info",
        "output":      question,
        "session_id":  session_id,
        "intent":      intent,
        "slots":       dict(state.slots),
        "ambiguity":   ambiguity,
        "stage_times": stage_times,
    }


def continue_session(session_id: str, answer: str) -> dict:
    """
    슬롯 필링 세션에 사용자 답변을 전달한다.

    Returns dict:
      status    : "need_info" | "complete" | "error"
      output    : 다음 질문(need_info) 또는 API URL(complete)
      session_id: need_info 일 때만
      intent    : 인텐트
      slots     : 현재 DST 상태
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
    print(f"[RAG DST] complete={state.complete}, pending={state.pending}, slots={state.slots}")

    if state.complete or not question:
        with _sessions_lock:
            _sessions.pop(session_id, None)
        url = _build_url(intent, state.slots)
        return {
            "status": "complete",
            "output": url,
            "intent": intent,
            "slots":  dict(state.slots),
        }

    return {
        "status":     "need_info",
        "output":     question,
        "session_id": session_id,
        "intent":     intent,
        "slots":      dict(state.slots),
    }