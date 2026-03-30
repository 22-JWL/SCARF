"""
모호성 분류기 학습 데이터 생성 스크립트 (v2)

document 구성 전략:
  KoE5로 query를 검색 → score gap 기반으로 top-k 카테고리 선택
  → 선택된 카테고리의 API description + useCase를 연결해서 document 구성

  이렇게 하면 학습 데이터가 실제 inference 시 classifier가 받는 입력과 동일한 형식이 됨

label 결정:
  A) Contrastive 데이터 (instruction, positive):
     - top-1 == positive 카테고리 AND gap 큼(단독 선택) → label=0 (명확)
     - top-1 == positive지만 gap 작음(여러 카테고리 선택) → label=1 (모호)
     - top-1 != positive 카테고리 → label=1 (오분류 가능성)
  B) test_queries_fixed.csv:
     - index_Classifier=1 → label=1 (모호)
     - index_Classifier=0 → label=0 (정확)

출력: data/processed/ambiguity/train/ambiguity_train_v2.jsonl
"""

import json
import os
import csv
import random
import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util

random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONTRASTIVE_DIR = os.path.join(BASE_DIR, "data", "processed", "retrieval", "train")
CATEGORY_DESC_PATH = os.path.join(BASE_DIR, "data", "category_description.json")
ACTION_PATH = os.path.join(BASE_DIR, "data", "action.json")
CSV_PATH = os.path.join(BASE_DIR, "data", "processed", "retrieval", "test", "test_queries_fixed.csv")
MODEL_PATH = os.path.join(BASE_DIR, "src", "checkpoints", "retrieval", "koe5_dense_retriever_f")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "processed", "ambiguity", "train", "ambiguity_train_v2.jsonl")

CONTRASTIVE_FILES = [
    os.path.join(CONTRASTIVE_DIR, "Contrastive_train_1.jsonl"),
    os.path.join(CONTRASTIVE_DIR, "Contrastive_train_2.jsonl"),
    os.path.join(CONTRASTIVE_DIR, "Contrastive_train_3.jsonl"),
]

GAP_THRESHOLD = 0.05   # 이 값보다 gap이 작으면 다음 카테고리도 포함
MAX_K = 3              # 최대 포함 카테고리 수


# ── 유틸 ──────────────────────────────────────────────────────────

def flatten_text(item):
    if isinstance(item, list):
        return " ".join(str(x) for x in item)
    return str(item)


def load_category_descriptions():
    with open(CATEGORY_DESC_PATH, "r", encoding="utf-8") as f:
        desc = json.load(f)
    return {k: flatten_text(v) for k, v in desc.items()}


def load_action_map():
    """카테고리별 API 목록 {category: [{description, useCase}, ...]}"""
    with open(ACTION_PATH, "r", encoding="utf-8") as f:
        actions = json.load(f)
    action_map = {}
    for api in actions:
        cat = api.get("category", "")
        if cat not in action_map:
            action_map[cat] = []
        action_map[cat].append({
            "description": api.get("description", ""),
            "useCase": api.get("useCase", ""),
        })
    return action_map


# ── KoE5 검색 + document 구성 ─────────────────────────────────────

def build_document(query, model, desc_embeddings, sub_categories, action_map):
    """
    query → KoE5 검색 → score gap 기반 top-k 카테고리 선택
    → 선택된 카테고리 API의 description+useCase 연결 → document 반환
    """
    query_emb = model.encode(query, convert_to_tensor=True, normalize_embeddings=True)
    scores = util.cos_sim(query_emb, desc_embeddings)[0]
    topk = torch.topk(scores, k=min(MAX_K + 1, len(sub_categories)))

    top_scores = topk.values.tolist()
    top_cats = [sub_categories[i] for i in topk.indices.tolist()]

    # gap 기반 k 결정
    selected_cats = [top_cats[0]]
    for i in range(len(top_scores) - 1):
        gap = top_scores[i] - top_scores[i + 1]
        if gap < GAP_THRESHOLD:
            selected_cats.append(top_cats[i + 1])
        else:
            break
        if len(selected_cats) >= MAX_K:
            break

    # 선택된 카테고리 API의 description + useCase 연결
    doc_parts = []
    for cat in selected_cats:
        apis = action_map.get(cat, [])
        for api in apis:
            desc = api.get("description", "").strip()
            use_case = api.get("useCase", "").strip()
            part = f"{desc} ({use_case})" if use_case else desc
            if part:
                doc_parts.append(part)

    document = " | ".join(doc_parts)
    return document, selected_cats, top_scores[:len(selected_cats)]


def get_label_from_retrieval(positive_cat, selected_cats):
    """
    top-1 == positive이고 단독 선택(gap 큼) → label=0 (명확)
    그 외 → label=1 (모호 또는 오분류)
    """
    if not selected_cats:
        return 1
    if selected_cats[0] == positive_cat and len(selected_cats) == 1:
        return 0
    return 1


# ── 데이터 생성 ───────────────────────────────────────────────────

def generate_from_contrastive(jsonl_paths, model, desc_embeddings, sub_categories, action_map):
    samples = []
    for path in jsonl_paths:
        if not os.path.exists(path):
            print(f"  [SKIP] 파일 없음: {path}")
            continue

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                query = data["instruction"]
                positive_text = flatten_text(data["positive"])

                # positive 카테고리 역추적 (category_desc에서 값으로 카테고리 찾기)
                positive_cat = None
                for cat, desc_text in zip(sub_categories, []):
                    pass
                # category_desc value → key 매핑
                positive_cat = cat_by_desc.get(positive_text)

                document, selected_cats, _ = build_document(
                    query, model, desc_embeddings, sub_categories, action_map
                )
                if not document:
                    continue

                label = get_label_from_retrieval(positive_cat, selected_cats)
                samples.append({
                    "query": query,
                    "document": document,
                    "label": label,
                })

    return samples


def generate_from_csv(csv_path, model, desc_embeddings, sub_categories, action_map):
    samples = []
    if not os.path.exists(csv_path):
        print(f"  [SKIP] CSV 없음: {csv_path}")
        return samples

    with open(csv_path, "r", encoding="euc-kr") as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = row.get("text", "").strip()
            idx_clf = row.get("index_Classifier", "").strip()
            if not query or idx_clf == "":
                continue

            document, _, _ = build_document(
                query, model, desc_embeddings, sub_categories, action_map
            )
            if not document:
                continue

            # index_Classifier=1 → 모호(label=1), index_Classifier=0 → 정확(label=0)
            label = int(idx_clf)
            samples.append({
                "query": query,
                "document": document,
                "label": label,
            })

    return samples


# ── main ──────────────────────────────────────────────────────────

def main():
    print("=== 모호성 분류기 학습 데이터 생성 (v2) ===\n")

    # 데이터 로드
    category_desc = load_category_descriptions()
    sub_categories = list(category_desc.keys())
    descriptions = list(category_desc.values())
    action_map = load_action_map()

    # positive text → category 역매핑 (Contrastive label 결정용)
    global cat_by_desc
    cat_by_desc = {v: k for k, v in category_desc.items()}

    print(f"카테고리 수: {len(sub_categories)}")
    print(f"GAP_THRESHOLD={GAP_THRESHOLD}, MAX_K={MAX_K}")

    # KoE5 모델 로드
    print(f"\nKoE5 모델 로드: {MODEL_PATH}")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(MODEL_PATH, device=device)

    # 카테고리 description 임베딩 (1회)
    print("카테고리 임베딩 계산 중...")
    desc_embeddings = model.encode(
        descriptions, convert_to_tensor=True, normalize_embeddings=True
    )

    # A) Contrastive 데이터
    print("\n[A] Contrastive 데이터에서 생성...")
    contrastive_samples = generate_from_contrastive(
        CONTRASTIVE_FILES, model, desc_embeddings, sub_categories, action_map
    )
    l0_a = sum(1 for s in contrastive_samples if s["label"] == 0)
    l1_a = sum(1 for s in contrastive_samples if s["label"] == 1)
    print(f"  label=0: {l0_a}, label=1: {l1_a}, 합계: {len(contrastive_samples)}")

    # B) test_queries_fixed.csv
    print("\n[B] test_queries_fixed.csv에서 생성...")
    csv_samples = generate_from_csv(
        CSV_PATH, model, desc_embeddings, sub_categories, action_map
    )
    l0_b = sum(1 for s in csv_samples if s["label"] == 0)
    l1_b = sum(1 for s in csv_samples if s["label"] == 1)
    print(f"  label=0: {l0_b}, label=1: {l1_b}, 합계: {len(csv_samples)}")

    # 합치기
    all_samples = contrastive_samples + csv_samples
    random.shuffle(all_samples)

    total_l0 = sum(1 for s in all_samples if s["label"] == 0)
    total_l1 = sum(1 for s in all_samples if s["label"] == 1)
    print(f"\n[전체] label=0: {total_l0}, label=1: {total_l1}, 합계: {len(all_samples)}")
    print(f"  비율 0:{total_l0/len(all_samples):.1%}  1:{total_l1/len(all_samples):.1%}")

    # 샘플 미리보기
    print("\n[샘플 미리보기 3건]")
    for s in all_samples[:3]:
        print(f"  query={s['query']}")
        print(f"  document={s['document'][:80]}...")
        print(f"  label={s['label']}\n")

    # 저장
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for sample in all_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print(f"저장 완료: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
