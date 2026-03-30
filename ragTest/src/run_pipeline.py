import json
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_chroma import Chroma   # pip install -U langchain-chroma
from langchain_core.documents import Document
from sentence_transformers import SentenceTransformer, util
import torch
import time
import os

from ambiguity_classifier import classify_ambiguity

MODEL_PATH = "checkpoints/retrieval/koe5_dense_retriever_f"
DESC_PATH = "../data/category_description.json"
ACTION_PATH = "../data/action.json"

# 1. 모델 로드
model = SentenceTransformer(MODEL_PATH, device="cpu")

# 2. subCategory description 로드
with open(DESC_PATH, "r", encoding="utf-8") as f: # 벡터화 한번만해서 저장
    category_desc = json.load(f)

sub_categories = []
descriptions = []

for k, v in category_desc.items():
    if isinstance(v, list):
        v = " ".join(v)
    sub_categories.append(k)
    descriptions.append(v)

# 3. description embedding (한 번만)
desc_embeddings = model.encode(
    descriptions,
    convert_to_tensor=True,
    normalize_embeddings=True
)

# 4. VectorStore 로드
# documents = load_documents_from_json(ACTION_PATH)
embeddings = HuggingFaceEmbeddings(
    model_name="nlpai-lab/KoE5",  # 🔥 학습 안 된 KoE5
    model_kwargs={"device": "cpu"}
)

# vectorstore = Chroma.from_documents(
#     documents,
#     embedding=embeddings,
#     persist_directory="./chroma_action_db",
#     collection_metadata={"hnsw:space": "cosine"}
# )


def load_documents_from_json(file_path="action.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        api_data = json.load(f)

    documents = []
    for api in api_data:
        content = (
            f"{api.get('windowName')}에서 "
            f"{api.get('api_name')} API를 사용하여 "
            f"{api.get('description')} "
            f"({api.get('useCase')})"
        )

        documents.append(
            Document(
                page_content=content,  # 🔍 검색용
                metadata={
                    "subCategory": api.get("category"),
                    "windowName": api.get("windowName"),
                    "api_name": api.get("api_name"),
                    "description": api.get("description"),
                    "useCase": api.get("useCase"),
                }
            )
        )

    print(f"✅ 문서 변환 완료: {len(documents)}개")
    return documents

def load_or_build_vectorstore(
    persist_dir,
    embeddings,
    action_path=None
):
    if os.path.exists(persist_dir):
        print("📦 기존 Chroma DB 로드")
        return Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings
        )

    print("🧱 Chroma DB 새로 생성")

    documents = load_documents_from_json(action_path)

    return Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_metadata={"hnsw:space": "cosine"}
    )


def classify_command(text):
    """
    입력: 자연어 명령 (str)
    출력: subCategory (str)
    """

    # 1. query embedding
    query_emb = model.encode(
        text,
        convert_to_tensor=True,
        normalize_embeddings=True
    )

    # 2. cosine similarity
    scores = util.cos_sim(query_emb, desc_embeddings)[0]
    topk = torch.topk(scores, k=3)

    # 3. Top-k 결과 처리
    score_top1 = float(topk.values[0])
    pred_top1 = sub_categories[topk.indices[0]]
    pred_top3 = [sub_categories[i] for i in topk.indices.tolist()]

    if score_top1 >= 0.75:
        return pred_top1, "auto"

    elif score_top1 >= 0.60:
        return pred_top3, "candidate"

    else:
        return "no_function", "reject"


def retrieve_action(sub_category, text, k=5):
    """
    입력:
      - subCategory (str or list)
      - 자연어 명령 (str)
    출력:
      - action.json 기반 API 후보 리스트
    """

    if isinstance(sub_category, list):
        filter_cond = {"subCategory": {"$in": sub_category}}
    else:
        filter_cond = {"subCategory": sub_category}

    results = vectorstore.similarity_search_with_score(
        query=text,
        k=k,
        filter=filter_cond
    )

    api_candidates = []
    for rank, (doc, score) in enumerate(results):
        api_candidates.append({
            "api_name": doc.metadata.get("api_name"),
            "windowName": doc.metadata.get("windowName"),
            "description": doc.metadata.get("description"),
            "useCase": doc.metadata.get("useCase"),
            "score": score,
            "rank": rank + 1,
            "confidence": (
                "high" if score >= 0.75
                else "mid" if score >= 0.55
                else "low"
            )
        })

    return api_candidates


def check_ambiguity(query, sub_category):
    """
    Stage 3: 모호성 판별

    Retriever가 분류한 subCategory가 실제로 맞는지 BGE-m3-ko 분류기로 검증.

    입력:
        query (str): 사용자 자연어 명령
        sub_category (str or list): Stage 1에서 분류된 subCategory
    출력:
        dict: {is_ambiguous, ambiguity_score, confidence}
    """
    if sub_category == "no_function":
        return {"is_ambiguous": False, "ambiguity_score": 0.0, "confidence": "rejected"}

    # list인 경우 (candidate 모드) top-1만 검증
    target_cat = sub_category[0] if isinstance(sub_category, list) else sub_category

    # 해당 카테고리의 description 가져오기
    desc = category_desc.get(target_cat, "")
    if isinstance(desc, list):
        desc = " ".join(desc)

    return classify_ambiguity(query, desc)


def main():
    global vectorstore

    embeddings = HuggingFaceEmbeddings(
        model_name="nlpai-lab/KoE5",
        model_kwargs={"device": "cpu"}
    )

    vectorstore = load_or_build_vectorstore(
        persist_dir="./chroma_action_db",
        embeddings=embeddings,
        action_path=ACTION_PATH
    )

    text = "임계값 올려"

    # Stage 1: subCategory 분류
    sub_category, mode = classify_command(text)

    # Stage 2: API 후보 검색
    actions = retrieve_action(sub_category, text)

    # Stage 3: 모호성 판별
    ambiguity = check_ambiguity(text, sub_category)

    print("📌 Stage 1 classify:", sub_category, mode)
    print("📌 Stage 2 actions:")
    for a in actions[:3]:
        print(a)
    print("📌 Stage 3 ambiguity:", ambiguity)


def measure_time():
#     model load: 0.82  # 최초 실행시에만 필요
#     📦 기존 Chroma DB 로드
#     vectorstore load: 0.11
#     first classify: 0.18
#     second classify: 0.11
    global vectorstore
    t0 = time.time()
    model = SentenceTransformer(MODEL_PATH, device="cpu")
    print("model load:", time.time() - t0)

    t1 = time.time()
    vectorstore = load_or_build_vectorstore(
        persist_dir="./chroma_action_db",
        embeddings=embeddings,
        action_path=ACTION_PATH
    )
    print("vectorstore load:", time.time() - t1)

    t2 = time.time()
    classify_command("임계값 올려")
    print("first classify:", time.time() - t2)

    t3 = time.time()
    classify_command("임계값 올려")
    print("second classify:", time.time() - t3)


if __name__ == "__main__":
    main()