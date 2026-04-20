# flask_LLM

반도체 패키징 검사 시스템(Gvision)을 위한 LLM 명령 실행 서버.
사용자의 자연어 명령을 받아 Gvision REST API 호출로 변환한다.

![로고이미지](./Scarf_overview.svg)


---

## 프로젝트 구조

```
flask_LLM/
├── app.py                    # Flask 서버 진입점
├── model_runner.py           # LLM 추론 및 모델 관리
├── intent_classifier.py      # DistilBERT 기반 Intent 분류기
├── whitelist_filter.py       # API URL 화이트리스트 검증
├── whitelist_getURL.py       # 허용 URL 목록 정의
├── prompt_combine_none.py    # 기본 시스템 프롬프트
├── prompt_classify_by_windows/ # 창별 특화 시스템 프롬프트
├── rag_pipeline.py           # SCARF 파이프라인 통합 모듈  
├── slot_url_builder.py       # 슬롯 → API URL 변환기       
├── ragTest/                  # SCARF 프레임워크 소스       
│   ├── src/
│   │   ├── run_pipeline.py           # Stage1/2 파이프라인
│   │   ├── ambiguity_classifier.py   # BGE-m3-ko 모호성 분류기
│   │   ├── dst_.py                   # DST 슬롯 필링 매니저
│   │   └── checkpoints/              # 학습된 모델 가중치
│   ├── experiment/slot_filling/      # SlotFillingModel 정의
│   └── data/
│       ├── action.json               # API 후보 목록 (vectorstore 소스)
│       ├── category_description.json # 카테고리 설명 (Stage1 retrieval)
│       └── slot_registry.json        # 슬롯 타입/후보값 정의
└── model_logs.csv            # 추론 로그
```

---

## 서버 실행

```bash
pip install flask flask-restx transformers torch accelerate
pip install sentence-transformers langchain-huggingface langchain-chroma
python app.py
```

기본 포트: `5000`

---

## API 엔드포인트

### `POST /instruct/`
자연어 명령을 받아 Gvision API를 실행한다.

**신규 명령:**
```json
{
  "text": "lga 임계값 100으로 올려줘",
  "model_name": "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"
}
```

**슬롯 필링 후속 답변** (need_info 응답 후):
```json
{
  "session_id": "20260312_143022",
  "answer": "lga"
}
```

**응답:**
```json
{
  "output": "/teaching/lga/update?propertyName=ScratchThreshold&value=100",
  "status": "complete",
  "intent": "set_threshold",
  "elapsed_time": 1.23,
  "gpu_memory": {"allocated_mb": 0.0, "reserved_mb": 0.0}
}
```

| `status` | 의미 |
|---|---|
| `complete` | API 실행 완료 |
| `need_info` | 슬롯 필링 중 — `output`에 질문, `session_id` 포함 |
| `error` | 오류 발생 |

### `POST /classify/`
문장의 intent를 분류한다.

### `POST /models/switch`
LLM 모델을 전환한다.

---

## SCARF 파이프라인

**SCARF**: Stage-wise Clarification-based Ambiguity-Resolving Framework

```
사용자 명령
    │
    ▼
Stage 1: Concept-level Retriever
  classify_command(text)
  → subCategory (category_description.json 기반 cosine similarity)
  → mode: "auto" / "candidate" / "reject"
    │
    ├─ reject → /NO_FUNCTION
    │
    ▼
Stage 2: Neural Relevance Scoring
  retrieve_action(subCategory, text)      ← action.json (Chroma vectorstore)
  → 상위 API 후보 목록
  classify_ambiguity(text, top_action_description)
  → is_ambiguous: "이 명령이 특정 API를 지목할 수 있는가?"
    │
    ├─ 명확 (low ambiguity)
    │       ▼
    │   Stage 3a: LLM 직접 호출
    │   run_model(text) → API URL 생성 → Gvision 실행
    │
    └─ 모호 (high ambiguity)
            ▼
        Stage 3b: 슬롯 필링
        DSTManager.process_first_utterance(text, intent)
        → 질문 반환 (세션 ID와 함께)
        → 유저 답변 수신 → continue_session(session_id, answer)
        → 슬롯 완성 시 slot_url_builder → API URL → Gvision 실행
```

### 슬롯 필링 세션
- 세션은 서버 메모리에 보관 (TTL: 5분)
- 멀티턴 대화로 누락된 파라미터를 순차적으로 수집
- 완성된 슬롯에서 URL을 빌드하여 Gvision API 직접 호출

---

## WPF 클라이언트 연동 (GvisionWpf)

`ChatWindowViewModel.cs` + `ApiServer.cs`

- 신규 명령 → `SendChatInputAsync`
- 슬롯 필링 후속 답변 → `SendSlotFillingAnswerAsync` (session_id + answer)
- 응답 `status == "need_info"` → 질문을 채팅 버블로 표시, session_id 저장
- 응답 `output == "/NO_FUNCTION"` → "죄송합니다. 저는 반도체 패키징 관련 요청만 처리합니다 다시 입력해주세요"
