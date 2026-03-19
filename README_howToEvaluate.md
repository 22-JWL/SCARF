# SCARF E2E 평가 패키지

## 파일 구성

```
├── app.py                    # Flask 서버 (수정됨)
├── rag_pipeline.py           # RAG 파이프라인 (수정됨)
├── evaluate_e2e.py           # E2E 평가 스크립트
├── test_queries_labeled_url.csv  # 평가 데이터 (246개)
└── README.md
```

---

## app.py 변경사항

| 항목 | 내용 |
|------|------|
| `DRY_RUN` 모드 추가 | 환경변수 `DRY_RUN=1` 설정 시 GVision API 실행 스킵 (평가 시 사용) |
| `slots` 응답 추가 | need_info / complete 반환 시 현재 DST 슬롯 상태 포함 |
| `is_ambiguous` 응답 추가 | Stage2 판단 결과 포함 |
| `stage_times` 응답 추가 | 각 스텝 소요시간 포함 (retriever / classifier / slot / exaone) |
| `output_model` 필드 추가 | 위 3개 필드 선언 추가 |

---

## rag_pipeline.py 변경사항

| 항목 | 내용 |
|------|------|
| `stage_times` 측정 추가 | Stage1(retriever), Stage2(classifier), Stage3(slot) 각각 소요시간 측정 |
| `slots` 반환 추가 | need_info / complete 반환 시 현재 DST 슬롯 상태 포함 |
| `RAGTEST_ROOT` 경로 | **본인 환경에 맞게 수정 필요** (아래 참고) |

### ⚠️ 경로 수정 필수

`rag_pipeline.py` 상단에서 본인 경로로 수정:

```python
RAGTEST_ROOT = r"C:\Users\AMLPC03\deepseers\ragTest"  # ← 본인 경로로 변경
```

---

## 평가 실행 방법

### 1. 서버 실행 (GVision 없이 평가 시)

```bash
# Windows
set DRY_RUN=1
python app.py
```

```bash
# GVision 켜고 실제 실행 시
python app.py
```

### 2. 평가 실행 (서버와 별도 터미널)

```bash
python evaluate_e2e.py
```

결과는 `eval_results/` 폴더에 저장됩니다.

---

## 평가 결과 설명

```
[Stage1] Intent Accuracy       → subCategory 분류 정확도
[Stage2] Ambiguity Accuracy    → 모호/명확 판단 정확도
[Stage3a] Slot Sample Accuracy → 발화 단위 슬롯 전체 일치율 (가장 엄격)
[Stage3a] All Slot Accuracy    → 슬롯 개별 일치율 (NONE 포함)
[Stage3a] Active Slot Accuracy → 실제 값이 있는 슬롯만 일치율 (핵심 지표)
[Stage3b] URL Exact Match      → LLM이 생성한 URL 정확도
```

### 현재 결과 (참고)

| Stage | 지표 | 수치 |
|-------|------|------|
| Stage1 | Intent Accuracy | 86.18% |
| Stage2 | Ambiguity Accuracy | 36.99% |
| Stage3a | Active Slot Accuracy | 66.67% (Stage2 우회 시) |
| Stage3b | URL Exact Match | 31.82% |

> **참고:** Stage3a Active Slot이 낮은 주요 원인은 Stage2가 슬롯 필링이 필요한 발화를 LLM으로 잘못 보내는 것. Stage2를 우회하고 전부 슬롯 필링으로 보내면 Active Slot 66.67%까지 올라감.

---

## Stage2 우회 테스트 방법

슬롯 필링 모델 단독 성능 확인 시 `rag_pipeline.py`에서 주석 처리:

```python
# 명확 → LLM  ← 이 블록 주석처리
# if not ambiguity["is_ambiguous"]:
#     return {
#         "status": "use_llm",
#         ...
#     }
```

서버 재시작 후 평가 실행하면 Stage2 영향 없이 슬롯 필링 성능만 측정 가능.
