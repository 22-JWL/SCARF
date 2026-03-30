# eval_result.py
from sentence_transformers import SentenceTransformer, util
from collections import defaultdict
from sklearn.model_selection import train_test_split
import csv, time, random, torch

random.seed(42)

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

corpus = {intent: desc for intent, desc in DESCRIPTIONS.items()}

# ── 공통 인코딩 함수 ──────────────────────────────────────────────
def get_desc_embeddings(model):
    return model.encode(
        ["passage: " + d for d in corpus.values()],
        convert_to_tensor=True,
        normalize_embeddings=True
    )

def predict(model, desc_embeddings, utt):
    sub_categories = list(corpus.keys())
    query_emb = model.encode("query: " + utt, convert_to_tensor=True, normalize_embeddings=True)
    scores = util.cos_sim(query_emb, desc_embeddings)[0]
    topk = torch.topk(scores, k=3)
    top1 = sub_categories[topk.indices[0]]
    top3 = [sub_categories[i] for i in topk.indices.tolist()]
    score = round(float(topk.values[0]), 4)
    return top1, top3, score

def save_csv(fname, data):
    if data:
        with open(fname, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        print(f"  → {fname} 저장완료 ({len(data)}개)")
    else:
        print(f"  → 틀린 것 없음!")

# ── 평가 1: utterance_intent.csv 기반 test split ─────────────────
def evaluate_split(model, model_name):
    rows = list(csv.DictReader(open("utterance_intent.csv", encoding="utf-8-sig")))
    by_intent = defaultdict(list)
    for r in rows:
        if r['intent'] in DESCRIPTIONS:
            by_intent[r['intent']].append(r['utterance'])
    if len(by_intent['system_setting']) > 200:
        by_intent['system_setting'] = random.sample(by_intent['system_setting'], 200)

    all_pairs = [(utt, intent) for intent, utts in by_intent.items() for utt in utts]
    _, temp = train_test_split(all_pairs, test_size=0.2, random_state=42, stratify=[p[1] for p in all_pairs])
    _, test_pairs = train_test_split(temp, test_size=0.5, random_state=42, stratify=[p[1] for p in temp])

    desc_embeddings = get_desc_embeddings(model)
    wrong_r1, wrong_r3, times = [], [], []

    for utt, true_intent in test_pairs:
        t0 = time.time()
        top1, top3, score = predict(model, desc_embeddings, utt)
        times.append(time.time() - t0)

        row = {"utterance": utt, "true": true_intent,
               "pred_top1": top1, "pred_top3": "|".join(top3), "score_top1": score}

        if top1 != true_intent:
            wrong_r1.append(row)
        if true_intent not in top3:
            wrong_r3.append(row)

    print(f"\n===== [{model_name}] utterance_intent 테스트 =====")
    print(f"평균 질의 시간 : {sum(times)/len(times)*1000:.2f}ms")
    print(f"Recall@1 틀림  : {len(wrong_r1)} / {len(test_pairs)}")
    print(f"Recall@3 틀림  : {len(wrong_r3)} / {len(test_pairs)}")
    save_csv(f"wrong_{model_name}_recall1.csv", wrong_r1)
    save_csv(f"wrong_{model_name}_recall3.csv", wrong_r3)

# ── 평가 2: test_queries_labeled_url.csv ─────────────────────────

TEST_QUERY_PATH = r"C:\Users\AMLPC03\deepseers\ragTest\experiment\slot_filling\test_queries_labeled_url.csv"

def evaluate_labeled(model, model_name):
    rows = list(csv.DictReader(open(TEST_QUERY_PATH, encoding="utf-8-sig")))
    desc_embeddings = get_desc_embeddings(model)
    wrong, times = [], []

    for r in rows:
        utt = r['text']
        true_intent = r['subCategory'].strip()
        if not true_intent:
            continue

        t0 = time.time()
        top1, top3, score = predict(model, desc_embeddings, utt)
        times.append(time.time() - t0)

        if top1 != true_intent:
            wrong.append({
                "id": r['id'],
                "utterance": utt,
                "true": true_intent,
                "pred_top1": top1,
                "pred_top3": "|".join(top3),
                "score_top1": score,
                "in_top3": true_intent in top3,
            })

    total = len([r for r in rows if r['subCategory'].strip()])
    print(f"\n===== [{model_name}] labeled 테스트 =====")
    print(f"평균 질의 시간 : {sum(times)/len(times)*1000:.2f}ms")
    print(f"Accuracy@1     : {(total - len(wrong)) / total:.4f}  ({total-len(wrong)}/{total})")
    print(f"틀린 것        : {len(wrong)}개")
    save_csv(f"wrong_{model_name}_labeled.csv", wrong)

# ── 실행 ──────────────────────────────────────────────────────────
for name, path in [("base", "nlpai-lab/KoE5"), ("finetuned", "./koe5_finetuned")]:
    m = SentenceTransformer(path, device="cpu")
    evaluate_split(m, name)
    evaluate_labeled(m, name)