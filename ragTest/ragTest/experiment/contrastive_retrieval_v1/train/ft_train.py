"""
ft_train.py
- 기존 파인튜닝된 koe5_finetuned 모델 기반으로 추가 학습
- 오답 발화를 hard example로 추가 반영
- augment CSV (추가 발화) 포함
"""

import random
import csv
from collections import defaultdict
from sklearn.model_selection import train_test_split
from sentence_transformers import SentenceTransformer, InputExample, losses, evaluation
from torch.utils.data import DataLoader
import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
import torch
import time
from sentence_transformers import util

# random.seed(42)

# HARD_NEG_RATIO = 0.7

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

# HARD_NEGATIVES = {
#     # 기존 유지 + 아래 추가
#     "inspection_execute":   ["calibration_control", "roi_collection_control", "ui_navigation_execute", "auto_configuration_execute"],
#     # calibration_control이 inspection_execute를 계속 잡아먹음 (id=92,94)

#     "set_size":             ["calibration_control", "set_threshold", "set_parameter", "geometry_set"],
#     # 보정창에서 사이즈 → calibration_control로 튐 (id=183,185)

#     "system_setting":       ["set_parameter", "recipe_management", "set_size", "inspection_execute", "calibration_control"],
#     # 색상/항목 활성화 발화가 calibration_control/set_size로 튐 (id=219,224,228,230)

#     "recipe_management":    ["system_setting", "history_control", "change_operation"],
#     # 프리셋 관련이 history_control/change_operation으로 튐 (id=210,212)

#     "ui_navigation_execute":["inspection_execute", "open_window", "change_operation"],
#     # 다음 탭 이동이 inspection_execute로 튐
# }
# # ── 오답 발화 (hard examples) ─────────────────────────────────────
# # # wrong_finetuned_labeled.csv 기반
# # HARD_EXAMPLES = [
# #     ("inspectRejectMark 버튼 눌러줘",                    "inspection_execute"),
# #     ("검사 버튼 눌러줘",                                  "inspection_execute"),
# #     ("lga 이물질 값 잘 확인해",                           "inspection_execute"),
# #     ("보정 창에서 사이즈 설정",                           "set_size"),
# #     ("보정창에서 사이즈 다시 지정",                       "set_size"),
# #     ("설정값 프리셋 저장",                                "recipe_management"),
# #     ("프리셋 작업 진행",                                  "recipe_management"),
# #     ("검사 색깔 빨간색으로",                              "system_setting"),
# #     ("레시피에서 Mapping 기능 사용 안 하도록 설정",        "system_setting"),
# #     ("BGA 검사에서 볼 피치 항목 사용하도록 켜",           "system_setting"),
# #     ("LGA 패드 사이즈 검사 항목 비활성화",                "system_setting"),
# #     ("세팅창에서 MAP 검사에서 이물질 항목 사용하도록 설정","system_setting"),
# #     ("다음 탭으로 이동",                                  "ui_navigation_execute"),
# # ]

# # ── 데이터 로드 ───────────────────────────────────────────────────
# def load_csv(path):
#     return list(csv.DictReader(open(path, encoding="utf-8-sig")))

# by_intent = defaultdict(list)

# # 기존 utterance_intent.csv
# for r in load_csv("utterance_intent.csv"):
#     if r['intent'] in DESCRIPTIONS:
#         by_intent[r['intent']].append(r['utterance'])

# # augment CSV (추가 발화)
# AUGMENT_PATH = "utterance_intent2.csv"  # augment_extra.csv + augment_color_attr.csv 합친 것
# try:
#     for r in load_csv(AUGMENT_PATH):
#         if r['intent'] in DESCRIPTIONS:
#             by_intent[r['intent']].append(r['utterance'])
#     print(f"[augment] {AUGMENT_PATH} 로드 완료")
# except FileNotFoundError:
#     print(f"[augment] {AUGMENT_PATH} 없음 → 스킵")

# # system_setting 상한
# MAX_SS = 250
# if len(by_intent['system_setting']) > MAX_SS:
#     by_intent['system_setting'] = random.sample(by_intent['system_setting'], MAX_SS)
#     print(f"[샘플링] system_setting → {MAX_SS}개")

# # ── train/val/test 분할 ───────────────────────────────────────────
# all_pairs = [(utt, intent) for intent, utts in by_intent.items() for utt in utts]

# train_pairs, temp_pairs = train_test_split(
#     all_pairs, test_size=0.2, random_state=42,
#     stratify=[p[1] for p in all_pairs]
# )
# val_pairs, test_pairs = train_test_split(
#     temp_pairs, test_size=0.5, random_state=42,
#     stratify=[p[1] for p in temp_pairs]
# )

# # 오답 발화 train에 강제 추가 (3회 반복으로 가중치 효과)
# # for pair in HARD_EXAMPLES * 3:
# #     train_pairs.append(pair)

# random.shuffle(train_pairs)
# print(f"train: {len(train_pairs)}  val: {len(val_pairs)}  test: {len(test_pairs)}")

# # ── InputExample 변환 ─────────────────────────────────────────────
# def to_examples(pairs):
#     all_intents = list(DESCRIPTIONS.keys())
#     examples = []
#     for utt, intent in pairs:
#         pos_desc = DESCRIPTIONS[intent]
#         hard_neg_pool = HARD_NEGATIVES.get(intent, [])
#         if hard_neg_pool and random.random() < HARD_NEG_RATIO:
#             neg_intent = random.choice(hard_neg_pool)
#         else:
#             neg_intent = random.choice([i for i in all_intents if i != intent])
#         neg_desc = DESCRIPTIONS[neg_intent]
#         examples.append(InputExample(texts=["query: " + utt, "passage: " + pos_desc]))#, "passage: " + neg_desc]))
#     return examples

# train_examples = to_examples(train_pairs)
# val_examples   = to_examples(val_pairs)
# print(f"train examples: {len(train_examples)}  val examples: {len(val_examples)}")

# # ── 모델 로드 (기존 파인튜닝 모델 기반) ──────────────────────────
# print("\n기존 koe5_finetuned 로드...")
# model = SentenceTransformer("./koe5_finetuned", device="cuda")
# print(next(model.parameters()).device)

# train_dataloader = DataLoader(
#     train_examples,
#     shuffle=True,
#     batch_size=64,
#     num_workers=0,
#     pin_memory=False,
# )

# train_loss = losses.MultipleNegativesRankingLoss(model)

# total_steps  = len(train_dataloader) * 3
# warmup_steps = int(total_steps * 0.05)  # 추가학습이라 warmup 짧게
# print(f"총 스텝: {total_steps}  warmup: {warmup_steps}")

# # val evaluator
# evaluator = evaluation.InformationRetrievalEvaluator(
#     queries={str(i): p[0] for i, p in enumerate(val_pairs)},
#     corpus={intent: desc for intent, desc in DESCRIPTIONS.items()},
#     relevant_docs={str(i): {p[1]} for i, p in enumerate(val_pairs)},
#     name="val",
# )

# # model.fit(
# #     train_objectives=[(train_dataloader, train_loss)],
# #     epochs=3,
# #     warmup_steps=warmup_steps,
# #     evaluator=evaluator,
# #     evaluation_steps=0,
# #     output_path="./koe5_finetuned_v2",
# #     save_best_model=True,
# #     show_progress_bar=True,
# #     use_amp=True,
# # )
# model.fit(
#     train_objectives=[(train_dataloader, train_loss)],
#     epochs=2,              # 3 → 2로 줄이기
#     warmup_steps=warmup_steps,
#     evaluator=None,        # ← evaluator 끄기! 이게 핵심
#     evaluation_steps=0,
#     output_path="./koe5_finetuned_v2",
#     save_best_model=False, # ← evaluator None이면 False로
#     show_progress_bar=True,
#     use_amp=True,
# )
# print("\n학습 완료 → ./koe5_finetuned_v2")

# ── test 평가 ─────────────────────────────────────────────────────
print("\n=== Test 평가 ===")
# best_model = SentenceTransformer("./koe5_finetuned_v2")
# corpus = {intent: desc for intent, desc in DESCRIPTIONS.items()}

# test_evaluator = evaluation.InformationRetrievalEvaluator(
#     queries={str(i): p[0] for i, p in enumerate(test_pairs)},
#     corpus=corpus,
#     relevant_docs={str(i): {p[1]} for i, p in enumerate(test_pairs)},
#     name="test",
# )
# results = test_evaluator(best_model)
# print("\n===== Test 결과 =====")
# for k, v in results.items():
#     print(f"{k}: {v:.4f}")

corpus      = {intent: desc for intent, desc in DESCRIPTIONS.items()}
sub_cats    = list(corpus.keys())
TEST_QUERY_PATH = r"C:\Users\AMLPC03\deepseers\ragTest\experiment\slot_filling\test_queries_labeled_url.csv"
MAX_SS      = 200

# ── 유틸 ─────────────────────────────────────────────────────────
def load_csv(path):
    return list(csv.DictReader(open(path, encoding="utf-8-sig")))

def save_csv(fname, data):
    if not data:
        print(f"  → {fname}: 틀린 것 없음")
        return
    with open(fname, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print(f"  → {fname} 저장완료 ({len(data)}개)")

def get_test_pairs():
    """utterance_intent.csv 기반 test split (원본만, utterance_intent2 제외)"""
    rows = load_csv("utterance_intent.csv")
    by_intent = defaultdict(list)
    for r in rows:
        if r['intent'] in DESCRIPTIONS:
            by_intent[r['intent']].append(r['utterance'])
    if len(by_intent['system_setting']) > MAX_SS:
        by_intent['system_setting'] = random.sample(by_intent['system_setting'], MAX_SS)
    all_pairs = [(utt, intent) for intent, utts in by_intent.items() for utt in utts]
    _, temp = train_test_split(all_pairs, test_size=0.2, random_state=42, stratify=[p[1] for p in all_pairs])
    _, test_pairs = train_test_split(temp, test_size=0.5, random_state=42, stratify=[p[1] for p in temp])
    return test_pairs

# ── 배치 평가 (빠른 버전) ────────────────────────────────────────
def batch_evaluate(model, pairs, tag):
    """pairs: [(utt, label), ...] → wrong 리스트 반환"""
    utts   = [p[0] for p in pairs]
    labels = [p[1] for p in pairs]

    desc_embs = model.encode(
        ["passage: " + d for d in corpus.values()],
        convert_to_tensor=True, normalize_embeddings=True, batch_size=64
    )
    t0 = time.time()
    q_embs = model.encode(
        ["query: " + u for u in utts],
        convert_to_tensor=True, normalize_embeddings=True, batch_size=64
    )
    elapsed = time.time() - t0

    scores = util.cos_sim(q_embs, desc_embs)
    wrong_r1, wrong_r3 = [], []

    for i in range(len(utts)):
        topk  = torch.topk(scores[i], k=3)
        top1  = sub_cats[topk.indices[0]]
        top3  = [sub_cats[j] for j in topk.indices.tolist()]
        score = round(float(topk.values[0]), 4)
        row   = {"utterance": utts[i], "true": labels[i],
                 "pred_top1": top1, "pred_top3": "|".join(top3),
                 "score_top1": score, "in_top3": labels[i] in top3}
        if top1 != labels[i]:   wrong_r1.append(row)
        if labels[i] not in top3: wrong_r3.append(row)

    total = len(utts)
    print(f"  평균 질의 시간 : {elapsed/total*1000:.2f}ms")
    print(f"  Accuracy@1    : {(total-len(wrong_r1))/total:.4f}  ({total-len(wrong_r1)}/{total})")
    print(f"  Recall@3 miss : {len(wrong_r3)}/{total}")

    # IR Evaluator 지표
    evaluator = evaluation.InformationRetrievalEvaluator(
        queries={str(i): u for i, u in enumerate(utts)},
        corpus=corpus,
        relevant_docs={str(i): {labels[i]} for i in range(total)},
        name=tag,
    )
    results = evaluator(model)
    for k, v in results.items():
        print(f"  {k}: {v:.4f}")

    return wrong_r1, wrong_r3

# ── 실행 ─────────────────────────────────────────────────────────
test_pairs = get_test_pairs()

labeled_rows = load_csv(TEST_QUERY_PATH)
labeled_pairs = [(r['text'], r['subCategory'].strip())
                 for r in labeled_rows if r['subCategory'].strip()]

models = [
    ("base",     "nlpai-lab/KoE5"),
    ("finetuned","./koe5_finetuned_v2"),
]

for name, path in models:
    print(f"\n{'='*55}")
    print(f"  모델: {name}")
    print(f"{'='*55}")
    m = SentenceTransformer(path, device="cpu")

    # 1,2: utterance_intent.csv test split
    print(f"\n[{name}] utterance_intent 테스트")
    w1, w3 = batch_evaluate(m, test_pairs, f"{name}_split")
    save_csv(f"wrong_{name}_split_recall1.csv", w1)
    save_csv(f"wrong_{name}_split_recall3.csv", w3)

    # 3,4: labeled 테스트
    print(f"\n[{name}] labeled 테스트")
    w1, w3 = batch_evaluate(m, labeled_pairs, f"{name}_labeled")
    save_csv(f"wrong_{name}_labeled_recall1.csv", w1)
    save_csv(f"wrong_{name}_labeled_recall3.csv", w3)