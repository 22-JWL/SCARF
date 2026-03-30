# SCARF: 반도체 후공정 장비 자연어 제어를 위한 다단계 모호성 탐지 프레임워크

**SCARF: Safe Clarification-based API Real-time Framework for Natural Language Control of Semiconductor Inspection Equipment**

이재욱¹, 주희연¹, 김무진², 한기준¹†
¹한성대학교 컴퓨터공학부, ²디에스
†Corresponding Author: keejun.han@hansung.ac.kr

**Keywords:** Natural Language Interface, Contrastive Learning, Dense Retrieval, Ambiguity Classification, Slot Filling, API Safety

---

## 1. 서론

### 연구 배경
- LLM의 발전으로 자연어 기반 장비 제어 시스템에 대한 수요가 증가하고 있음
- 반도체 패키징 장비는 **수백 가지 API**를 통해 제어되는 고정밀 시스템
- **핵심 위험 — 모호한 입력 질의의 무검증 실행**
  - 예: "임계값 올려" → 어떤 검사 항목? 어느 수준? → LLM이 임의 파라미터로 API 호출
  - 결과: 검사 결과 오분류, 불량품 미검출, **장비 손상**
- 기존 RAG 기반 접근법은 검색 결과의 **의미적 일치성 검증 단계가 부재**하여 안전 크리티컬 환경에 부적합

### 연구 목적
- 모호한 자연어 쿼리를 **사전 탐지**하고 필요한 정보를 **선택적으로 확보**
- 단계별 검증 구조로 불필요한 실행을 **조기 차단** → 안전성 + 효율성 동시 달성
- 검증된 요청에 한해 LLM을 통한 장비 동작 실행

---

## 2. 제안 방법: SCARF 프레임워크

### 2.1 전체 파이프라인

| 단계 | 명칭 | 역할 | 모델 |
|:----:|------|------|------|
| **Stage 1** | 계층적 의미 검색 | 사용자 발화 → 18개 카테고리 분류 | KoE5 + ChromaDB |
| **Stage 2** | 모호성 분류기 | 후보 API 검색 + 모호성 판별 | BGE-m3-korean (SBERT) |
| **Stage 3a** | Clear Path | 명확한 입력 → LLM 직접 추론 | EXAONE-3.5-2.4B |
| **Stage 3b** | Ambiguous Path | 모호한 입력 → 슬롯 필링 → URL 빌드 | KLUE/RoBERTa-base (DST) |

- 각 단계에서 불필요한 실행을 조기 차단하는 **순차적 검증 구조**
- 검증된 요청에 한해 장비 동작 실행 → 부적절한 장비 동작 방지

### 2.2 Hybrid Tag 기반 구조화 메타데이터
- 반도체 장비 API의 복합 메타데이터(Window, Tab, API명, 파라미터)를 **Hybrid Tag** 형식으로 구조화
  ```
  [창: bga(비지에이)] [탭: Package(패키지)] [명령어: bga_auto_threshold_set]
  [파라미터: propertyName, value] 대상의 특성을 분석하여 임계값을 자동으로 설정합니다.
  ```
- 한글 음차 표기 병기 → **한국어 발화와 영문 API 메타데이터 간 의미적 정렬** 강화

### 2.3 BERT 기반 대조학습 모호성 분류기 (Stage 2)
- **모델**: BGE-m3-korean Bi-Encoder (Sentence-BERT 아키텍처)
- **학습**: Multiple Negatives Ranking Loss (MNRL) 대조 학습
  - 명확한 발화 → Top-1 API 유사도 압도적 (**높은 마진**)
  - 모호한 발화 → 복수 API 유사도 분산 (**낮은 마진**)
- **판별**: Top-1 vs Top-2 코사인 유사도 마진 < 임계값(θ) → **Ambiguous**
- **데이터**: 언더샘플링 + 규칙 기반 증강으로 클래스 불균형 해소

### 2.4 DST 기반 슬롯 필링 (Stage 3b)
- KLUE/RoBERTa-base 기반 Dialog State Tracking
- 모호한 입력 → 누락 슬롯 순차 질의 → 다중 턴 명확화
- 모든 필수 슬롯 충족 시 **URL Builder**가 최종 API URL 자동 생성

---

## 3. 실험 환경

| 항목 | 내용 |
|------|------|
| **테스트 데이터** | 218개 쿼리 (18개 제어 카테고리 균등 분포) |
| **비교 모델** | ProCoT (Deng et al., EMNLP 2023) — GPT 기반 Proactive Chain-of-Thought |
| **평가 지표** | API URL 정확도 (Exact Match), 평균 추론 소요 시간 |
| **공정 비교 조건** | 동일 GT 슬롯 정보, 동일 최대 턴 수 (10턴), URL 미생성 = 오답 |
| **하드웨어** | Intel Core Ultra 9 285K, NVIDIA RTX 5090 32GB |

---

## 4. 실험 결과

### 4.1 정확도 비교 (API URL Exact Match)

| 모델 | 정확 | 전체 | **정확도** |
|------|:----:|:----:|:---------:|
| ProCoT (GPT) | 187 | 218 | 85.71% |
| **SCARF (Ours)** | **197** | **218** | **90.37%** |

- SCARF는 ProCoT 대비 **+4.66%p 정확도 향상**
- 모호한 입력에서 DST 슬롯 필링이 LLM 단독 추론보다 안정적

### 4.2 추론 속도 비교

| 모델 | **평균 소요 시간** | 속도 비율 |
|------|:-----------------:|:---------:|
| ProCoT (GPT) | 5.904초 | 1.0x |
| **SCARF (Ours)** | **0.214초** | **27.6x** |

- SCARF는 ProCoT 대비 **약 27.6배 빠른 추론 속도**
- 경량 온디바이스 모델 → 외부 API 호출 없이 실시간 장비 제어 가능

### 4.3 SCARF 파이프라인 구간별 지연 시간

| 구간 | 소요 시간 | 비율 |
|------|:---------:|:----:|
| Stage 1 (계층적 의미 검색) | 0.025초 | 9.6% |
| Stage 2 (모호성 분류기) | 0.021초 | 8.1% |
| Stage 3 (최종 추론) | 0.214초 | 82.3% |
| **합계** | **0.260초** | 100% |

- Stage 3 세부: Clear Path(LLM) 평균 0.392초 / Ambiguous Path(SlotFilling) 평균 0.100초
- Stage 1–2 합산 **46ms** → 모호성 판별까지 극도로 경량

### 4.4 ProCoT 다중 턴 분석

| 턴 수 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 9 |
|:-----:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 건수 | 65 | 38 | 42 | 27 | 34 | 1 | 9 | 2 |

- 평균 **2.90턴** (최대 9턴) — 1턴 완료 비율 29.8%에 불과
- 턴 수 증가 시 GPT API 호출 비용 및 지연 시간 선형 증가

---

## 5. 결론

- **SCARF**는 BERT 기반 대조학습으로 질의의 의미적 정합성을 검증하고, 슬롯 필링으로 필수 정보 충족을 확인하는 **다단계 검증 파이프라인**
- 검증된 요청에 한해 LLM 장비 동작 실행 → **부적절한 장비 동작을 효과적으로 방지**
- GPT 기반 ProCoT 대비 **정확도 +4.66%p (90.37%), 속도 27.6배 (0.214초)**
- 경량 온디바이스 모델 구성 → **외부 API 의존 없이** 생산 현장 실시간 배포 가능
