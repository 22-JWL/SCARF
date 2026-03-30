"""
Ambiguity Classifier Training Data Generator

[입력 소스]
  - TestData100.csv              → text 컬럼
  - ambiguity_question_184.csv  → text 컬럼
  - Contrastive_train_1~3.jsonl → instruction 필드

[파이프라인]
  User NL Input
    → Stage 1 : classify_command()   → sub_category / mode
    → Stage 2a: vectorstore 검색     → top-k 후보 (score 포함)
    → score_gap 필터 + [:3]          → classify_ambiguity()에 전달될 document
    → 화면 표시 후 사용자 레이블 입력

[입력 키]
  0 → label=0 (명확: 특정 API 하나를 가리킴)
  1 → label=1 (모호: 어떤 API인지 이 명령만으로 불분명)
  s → 건너뜀
  q → 저장 후 종료

[출력]
  ragTest/data/processed/ambiguity/train/ambiguity_train_[YYYYMMDD].jsonl
  (중단 후 재실행 시 이미 레이블링한 query 자동 스킵)
"""

import sys
import os
import json
import glob
import csv
from datetime import datetime

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
current_dir  = os.path.dirname(os.path.abspath(__file__))
RAGTEST_ROOT = os.path.abspath(os.path.join(current_dir, "..", ".."))   # ragTest/
RAGTEST_SRC  = os.path.join(RAGTEST_ROOT, "src")

DATA_ROOT    = os.path.join(RAGTEST_ROOT, "data")
RETRIEVAL_DIR = os.path.join(DATA_ROOT, "processed", "retrieval")
OUT_DIR      = os.path.join(DATA_ROOT, "processed", "ambiguity", "train")

# 입력 파일 경로
CSV_FILES = {
    "TestData100":           os.path.join(RETRIEVAL_DIR, "test", "TestData100.csv"),
    "ambiguity_question_184": os.path.join(RETRIEVAL_DIR, "test", "ambiguity_question_184.csv"),
    "ambiguity_train": os.path.join(RETRIEVAL_DIR, "test", "ambiguity_train.csv"),

}
CONTRASTIVE_DIR = os.path.join(RETRIEVAL_DIR, "train")

# 출력 파일 (날짜 기반)
OUTPUT_PATH = os.path.join(OUT_DIR, f"ambiguity_train_{datetime.now().strftime('%Y%m%d')}.jsonl")

# run_pipeline 임포트 전 CWD 변경
os.chdir(RAGTEST_SRC)
sys.path.insert(0, RAGTEST_SRC)

from langchain_huggingface import HuggingFaceEmbeddings
import run_pipeline

# ── 상수 ─────────────────────────────────────────────────────────────────────
RETRIEVAL_K         = 5
SCORE_GAP_THRESHOLD = 0.15   # 상대 조건: top-1 대비 거리 차이 (코사인 거리)
MAX_DISTANCE        = 0.45   # 절대 조건: 최대 허용 거리 (0.45 ≈ similarity 0.55)


# ── 데이터 수집 ───────────────────────────────────────────────────────────────

def load_queries() -> list[dict]:
    """
    모든 소스에서 query 수집. 중복 제거 후 source / sub_category 정보 포함하여 반환.
    Returns: [{"query": str, "source": str, "sub_category": str | None}, ...]
    """
    seen   = set()
    result = []

    def add(query: str, source: str, sub_category: str | None = None):
        q = query.strip()
        if q and q not in seen:
            seen.add(q)
            result.append({"query": q, "source": source, "sub_category": sub_category})

    # CSV 파일들 (text 컬럼, subCategory 컬럼 있으면 함께 저장)
    for name, path in CSV_FILES.items():
        if not os.path.exists(path):
            print(f"  [건너뜀] 파일 없음: {path}")
            continue
        for enc in ("utf-8-sig", "utf-8", "euc-kr", "cp949"):
            try:
                with open(path, "r", encoding=enc) as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                for row in rows:
                    add(row.get("text", ""), name, row.get("subCategory") or None)
                print(f"  {name}: 로드 완료 ({enc})")
                break
            except (UnicodeDecodeError, Exception):
                continue
        else:
            print(f"  [오류] {name}: 인코딩 감지 실패")

    # Contrastive_train_*.jsonl (instruction 필드)
    for fpath in sorted(glob.glob(os.path.join(CONTRASTIVE_DIR, "Contrastive_train_*.jsonl"))):
        fname = os.path.basename(fpath)
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    item = json.loads(line)
                    add(item.get("instruction", ""), fname)
        print(f"  {fname}: 로드 완료")

    return result


def load_done_queries() -> set[str]:
    """오늘 날짜 파일에 이미 저장된 query 집합 (재시작용)"""
    done = set()
    if not os.path.exists(OUTPUT_PATH):
        return done
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    done.add(json.loads(line)["query"])
                except json.JSONDecodeError:
                    print(f"  [경고] 손상된 라인 건너뜀: {line[:60]}...")
    return done


# ── 파이프라인 ────────────────────────────────────────────────────────────────

def run_pipeline_for_query(query: str, sub_category: str | None = None) -> dict | None:
    """
    Stage1 + Stage2a 실행.
    sub_category가 주어지면 Stage1(classify_command)을 건너뜀.
    Returns: {
        sub_category, mode,
        candidates: [{description, useCase, api_name, score, gap}, ...],
        document: str  ← classify_ambiguity()에 전달될 실제 텍스트
    }
    None이면 Stage1 reject 또는 후보 없음.
    """
    if sub_category:
        mode = "auto"
    else:
        sub_category, mode = run_pipeline.classify_command(query)
        if mode == "reject":
            return None

    # 전체 vectorstore 검색 (subCategory 필터 없음)
    results = run_pipeline.vectorstore.similarity_search_with_score(
        query=query,
        k=RETRIEVAL_K,
    )
    if not results:
        return None

    # score = 코사인 거리 (낮을수록 유사)
    # top_score = 가장 낮은 거리 (가장 유사한 후보)
    top_score = results[0][1]
    # sub_category가 주어진 경우 절대 거리 조건(MAX_DISTANCE)을 무시
    use_distance_filter = sub_category is None
    candidates = []
    for doc, score in results:
        gap = score - top_score  # top-1보다 얼마나 더 먼지 (항상 >= 0)
        candidates.append({
            "api_name":    doc.metadata.get("api_name", ""),
            "description": doc.metadata.get("description", ""),
            "useCase":     doc.metadata.get("useCase", ""),
            "score":       score,
            "gap":         gap,
            "in_document": (
                gap <= SCORE_GAP_THRESHOLD   # top-1과 거리 차이가 작음
                and (not use_distance_filter or score <= MAX_DISTANCE)
            ),
        })

    # document 생성 (= classify_ambiguity의 document_text 인자)
    # 두 조건(gap + min_score) 만족 후보 중 최대 3개
    selected = [c for c in candidates if c["in_document"]][:3]
    # sub_category가 주어졌는데도 후보가 없으면 top-1 강제 포함
    if not selected:
        selected = [candidates[0]]
        candidates[0]["in_document"] = True
    doc_parts = []
    for c in selected:
        line = c["description"]
        if c["useCase"]:
            line += f" ({c['useCase']})"
        if line.strip():
            doc_parts.append(line)

    document = "\n".join(doc_parts)
    if not document:
        return None

    sub_str = sub_category if isinstance(sub_category, str) else " / ".join(sub_category)

    return {
        "sub_category": sub_str,
        "mode":         mode,
        "candidates":   candidates,
        "document":     document,
    }


# ── 화면 출력 ─────────────────────────────────────────────────────────────────

def display(query: str, source: str, info: dict, idx: int, total: int):
    """레이블링 화면 출력"""
    print("\n" + "=" * 70)
    print(f"  [{idx}/{total}]  출처: {source}")
    print(f"  Stage1 → {info['mode']:9s}  인텐트: {info['sub_category']}")
    print("=" * 70)
    print(f"  Query : {query}")
    print("-" * 70)
    print(f"  {'#':<3} {'score':>6}  {'gap':>6}  {'포함':^4}  description")
    print("-" * 70)

    in_doc_count = 0
    for i, c in enumerate(info["candidates"], 1):
        in_doc_count += c["in_document"]
        mark = "◀" if c["in_document"] and in_doc_count <= 3 else ""
        desc = c["description"]
        if len(desc) > 42:
            desc = desc[:42] + "…"
        print(f"  {i:<3} {c['score']:>6.4f}  {c['gap']:>6.4f}  {mark:^4}  {desc}")

    print("-" * 70)
    print("  ◀ = score_gap 필터 통과 → classify_ambiguity() document에 포함")
    print()
    print("  [classify_ambiguity() 입력]")
    print(f"    query    : {query}")
    print(f"    document :")
    for line in info["document"].split("\n"):
        print(f"               {line}")
    print()
    print("  0 = 명확 (이 명령 → 특정 API 하나를 가리킴)")
    print("  1 = 모호 (이 명령만으로는 어떤 API인지 불분명)")
    print("  s = 건너뜀   q = 저장 후 종료")
    print()


def get_input() -> str:
    while True:
        val = input("  입력 → ").strip().lower()
        if val in ("0", "1", "s", "q"):
            return val
        print("  0, 1, s, q 중 하나를 입력하세요.")


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  Ambiguity Classifier Training Data Generator")
    print("=" * 70)

    # Vectorstore 초기화
    print("\n[1] Vectorstore 초기화...")
    embeddings = HuggingFaceEmbeddings(
        model_name="nlpai-lab/KoE5",
        model_kwargs={"device": "cpu"},
    )
    run_pipeline.vectorstore = run_pipeline.load_or_build_vectorstore(
        persist_dir="./chroma_action_db",
        action_path="../data/action.json",
        embeddings=embeddings,
    )
    doc_count = run_pipeline.vectorstore._collection.count()
    print(f"  컬렉션 문서 수: {doc_count}")
    if doc_count == 0:
        print("  ⚠ 기존 DB가 비어있음 → 메모리 내 임시 빌드...")
        from langchain_chroma import Chroma
        documents = run_pipeline.load_documents_from_json("../data/action.json")
        run_pipeline.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            collection_metadata={"hnsw:space": "cosine"},
        )
        print(f"  빌드 완료: {run_pipeline.vectorstore._collection.count()}개 문서 (메모리 전용)")

    # Query 수집
    print("\n[2] Query 수집...")
    all_entries  = load_queries()
    done_queries = load_done_queries()

    pending = [e for e in all_entries if e["query"] not in done_queries]
    # Stage1 reject 제외 (미리 필터링하지 않고 런타임에 처리)

    already = len(done_queries)
    total   = already + len(pending)
    print(f"\n  전체 {len(all_entries)}개 (중복 제거)  |  완료 {already}개  |  남은 {len(pending)}개")
    print(f"  출력 파일: {OUTPUT_PATH}\n")

    if not pending:
        print("모든 query 레이블링 완료!")
        return

    # 레이블링 루프
    os.makedirs(OUT_DIR, exist_ok=True)
    out_f   = open(OUTPUT_PATH, "a", encoding="utf-8")
    saved   = 0
    skipped = 0
    idx     = already

    try:
        for entry in pending:
            query        = entry["query"]
            source       = entry["source"]
            sub_category = entry.get("sub_category")

            info = run_pipeline_for_query(query, sub_category)
            if info is None:
                continue  # Stage1 reject → 조용히 스킵

            idx += 1
            display(query, source, info, idx, total)
            val = get_input()

            if val == "q":
                print("\n  저장 후 종료합니다.")
                break
            elif val == "s":
                skipped += 1
                continue
            else:
                record = {
                    "query":    query,
                    "document": info["document"],
                    "label":    int(val),
                    "source":   source,
                }
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_f.flush()
                saved += 1

    finally:
        out_f.close()

    # 최종 통계
    print(f"\n[완료]  저장 {saved}개  |  건너뜀 {skipped}개")
    if os.path.exists(OUTPUT_PATH):
        records = []
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        l0 = sum(1 for r in records if r["label"] == 0)
        l1 = sum(1 for r in records if r["label"] == 1)
        print(f"  누적: {len(records)}개  (label=0: {l0}개 / label=1: {l1}개)")
        print(f"  파일: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
