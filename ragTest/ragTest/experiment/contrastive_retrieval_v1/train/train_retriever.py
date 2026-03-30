"""
train_retriever.py
26/3/26 -> 데이터 500개에서 ->
인텐트별 개수: system_setting 632 / 총 3598개
인텐트별 개수:

intent
system_setting                632
ui_navigation_execute         213
calibration_control           203
set_threshold                 198
open_window                   194
geometry_set                  190
roi_collection_control        188
set_option                    178
no_function                   173
history_control               171
inspection_execute            167
set_size                      166
recipe_management             162
auto_configuration_execute    158
set_parameter                 153
change_operation              152
close_windows                 150
chat_clear                    150
Name: count, dtype: int64

총 데이터 개수: 3598
인텐트 종류 개수: 18
-> 위와 같이 늘리고 학습

KoE5 fine-tuning with MultipleNegativesRankingLoss
- hard negative 70% + random negative 30% 혼합 (Mixed Negative Sampling)
- system_setting 상한 200개 샘플링
- train 80 / val 10 / test 10 stratified 분할
"""

import random
import csv
from collections import defaultdict
from sklearn.model_selection import train_test_split
from sentence_transformers import SentenceTransformer, InputExample, losses, evaluation
from torch.utils.data import DataLoader
import torch
device = "cuda" if torch.cuda.is_available() else "cpu"
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0))

random.seed(42)

HARD_NEG_RATIO = 0.7  # hard negative 비율 (나머지 0.3은 random negative)

# ── 1. category description ───────────────────────────────────────
DESCRIPTIONS = {
    "system_setting":            "장비의 시스템 설정을 조정합니다. 예: 레시피 파라미터, 저장 옵션, 기능 활성/비활성화, 색상 변경. 가로·세로 길이 설정 등",
    "open_window":               "UI 창을 열어 작업 화면이나 티칭 화면을 표시합니다.",
    "geometry_set":              "ROI의 위치, 좌표, 영역 범위를 숫자로 지정합니다.",
    "set_threshold":             "검사할 대상이 패키지 표면에서 명확히 구분되도록 임계값을 설정합니다.",
    "inspection_execute":        "검사 또는 티칭 테스트를 실행하고 결과를 반환합니다.",
    "ui_navigation_execute":     "UI에서 특정 탭으로 이동하는 조작을 수행합니다.",
    "set_size":                  "검사 대상의 크기 최소/최대 값을 설정합니다.",
    "set_option":                "패키지나 핀 등의 설정 옵션을 변경합니다. 예: Edge 방향, Edge 모드, 첫 번째 핀 타입, 회전각도.",
    "roi_collection_control":    "ROI를 새로 만들거나 삭제할 때 사용하는 명령입니다.",
    "auto_configuration_execute":"자동 구성 기능으로 자동으로 임계값이나 ROI 값을 설정합니다.",
    "history_control":           "검사 기록에서 데이터 필터링 조건을 설정하여 불필요한 정보를 걸러냅니다.",
    "calibration_control":       "장비 보정 관련 파라미터를 조정하여 검사 정확도를 확보합니다.",
    "no_function":               "지원하지 않는 명령이나 장비와 관련 없는 요청, 잡담.",
    "change_operation":          "소프트웨어의 동작 모드를 변경합니다.",
    "set_parameter":             "검사 또는 장비 동작에 필요한 세부 파라미터를 설정합니다. 예: OutlineWidth, Edge Threshold Amplitude",
    "chat_clear":                "채팅창의 대화 기록을 초기화합니다.",
    "close_windows":             "열려 있는 UI 창을 닫습니다.",
    "recipe_management":         "레시피(Preset)를 관리합니다. 예: 추가, 복사, 삭제, 적용",
}

# ── 2. 하드 네가티브 페어링 ────────────────────────────────────────
HARD_NEGATIVES = {
    "set_threshold":             ["set_size", "set_parameter", "set_option"],
    "set_size":                  ["set_threshold", "set_parameter", "geometry_set"],
    "set_parameter":             ["set_threshold", "set_option", "system_setting"],
    "set_option":                ["set_parameter", "set_threshold", "calibration_control"],
    "geometry_set":              ["roi_collection_control", "set_size"],
    "roi_collection_control":    ["geometry_set", "inspection_execute"],
    "inspection_execute":        ["roi_collection_control", "ui_navigation_execute", "auto_configuration_execute"],
    "ui_navigation_execute":     ["inspection_execute", "open_window"],
    "open_window":               ["close_windows", "ui_navigation_execute"],
    "close_windows":             ["open_window"],
    "calibration_control":       ["set_option", "set_parameter"],
    "history_control":           ["system_setting", "inspection_execute"],
    "system_setting":            ["set_parameter", "recipe_management"],
    "recipe_management":         ["system_setting"],
    "change_operation":          ["ui_navigation_execute", "open_window"],
    "auto_configuration_execute":["inspection_execute", "set_threshold"],
    "chat_clear":                ["no_function", "close_windows"],
    "no_function":               ["chat_clear", "change_operation"],
}

# ── 3. 데이터 로드 ────────────────────────────────────────────────
rows = list(csv.DictReader(open("utterance_intent.csv", encoding="utf-8-sig")))

by_intent = defaultdict(list)
for r in rows:
    if r['intent'] in DESCRIPTIONS:
        by_intent[r['intent']].append(r['utterance'])

# system_setting 상한 200개
MAX_SS = 200
if len(by_intent['system_setting']) > MAX_SS:
    by_intent['system_setting'] = random.sample(by_intent['system_setting'], MAX_SS)
    print(f"[샘플링] system_setting → {MAX_SS}개")

# ── 4. train / val / test 분할 (stratified) ───────────────────────
all_pairs = [(utt, intent)
             for intent, utts in by_intent.items()
             for utt in utts]

train_pairs, temp_pairs = train_test_split(
    all_pairs, test_size=0.2, random_state=42,
    stratify=[p[1] for p in all_pairs]
)
val_pairs, test_pairs = train_test_split(
    temp_pairs, test_size=0.5, random_state=42,
    stratify=[p[1] for p in temp_pairs]
)

print(f"train: {len(train_pairs)}  val: {len(val_pairs)}  test: {len(test_pairs)}")

# ── 5. InputExample 변환 (mixed negative sampling) ────────────────
def to_examples(pairs):
    all_intents = list(DESCRIPTIONS.keys())
    examples = []
    for utt, intent in pairs:
        pos_desc = DESCRIPTIONS[intent]
        hard_neg_pool = HARD_NEGATIVES.get(intent, [])

        # 70% hard negative / 30% random negative
        if hard_neg_pool and random.random() < HARD_NEG_RATIO:
            neg_intent = random.choice(hard_neg_pool)
        else:
            neg_intent = random.choice([i for i in all_intents if i != intent])

        neg_desc = DESCRIPTIONS[neg_intent]
        examples.append(InputExample(texts=[utt, pos_desc]))# neg desc
    return examples

train_examples = to_examples(train_pairs)
val_examples   = to_examples(val_pairs)

print(f"train examples: {len(train_examples)}  val examples: {len(val_examples)}")

# ── 6. 모델 & 학습 ───────────────────────────────────────────────
model = SentenceTransformer("nlpai-lab/KoE5", device="cuda")
print(next(model.parameters()).device)
train_dataloader = DataLoader(
    train_examples,
    shuffle=True,
    batch_size=64,       # 32 → 64로 올려요
    num_workers=0,
    pin_memory=False,    # True → False
)
train_loss = losses.MultipleNegativesRankingLoss(model)

total_steps  = len(train_dataloader) * 5
warmup_steps = int(total_steps * 0.1)
print(f"총 스텝: {total_steps}  warmup: {warmup_steps}")

# val evaluator
val_queries  = {str(i): p[0] for i, p in enumerate(val_pairs)}
val_corpus   = {intent: desc for intent, desc in DESCRIPTIONS.items()}
val_relevant = {str(i): {p[1]} for i, p in enumerate(val_pairs)}

evaluator = evaluation.InformationRetrievalEvaluator(
    queries=val_queries,
    corpus=val_corpus,
    relevant_docs=val_relevant,
    name="val",
)

model.fit(
    train_objectives=[(train_dataloader, train_loss)],
    epochs=3,
    warmup_steps=warmup_steps,
    evaluator=evaluator,
    evaluation_steps=0,
    output_path="./koe5_finetuned",
    save_best_model=True,
    show_progress_bar=True,
    use_amp=False,       # True → False
)

print("\n학습 완료 → ./koe5_finetuned")

# ── 7. test 평가 ─────────────────────────────────────────────────
print("\n=== Test 평가 ===")
best_model = SentenceTransformer("./koe5_finetuned")

test_queries  = {str(i): p[0] for i, p in enumerate(test_pairs)}
test_relevant = {str(i): {p[1]} for i, p in enumerate(test_pairs)}

test_evaluator = evaluation.InformationRetrievalEvaluator(
    queries=test_queries,
    corpus=val_corpus,  # corpus는 동일한 18개 description
    relevant_docs=test_relevant,
    name="test",
)
test_evaluator(best_model)