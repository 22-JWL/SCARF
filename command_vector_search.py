# command_vector_search.py : test_search.py 함수 구조 리팩토링 [test]

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import chromadb
from sklearn.metrics.pairwise import cosine_similarity

class CommandVectorSearch:
    def __init__(
        self,
        csv_path="all_commands.csv",
        chroma_path="./chroma_db",
        collection_name="commands",
        embedding_model_name='all-MiniLM-L6-v2',
        force_reload=False,
    ):
        # 1. DB/모델 로드
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.command_col = self.client.get_or_create_collection(collection_name)
        print(f"✅ '{collection_name}' 컬렉션 준비 완료")
        self.df_commands = pd.read_csv(csv_path)
        self.df_commands['id'] = self.df_commands.index.astype(str)

        # 2. 임베딩
        self.model = SentenceTransformer(embedding_model_name)
        self.embeddings_list = self.model.encode(
            self.df_commands['text'].tolist(), show_progress_bar=True
        ).tolist()

        # 3. 벡터DB 동기화(중복건 제외)
        if force_reload:
            self.command_col.delete(where={})  # 전체 리셋

        try:
            existing_docs = self.command_col.get(ids=None, include=['ids'])
            existing_ids = set(existing_docs['ids'])
        except:
            existing_ids = set()

        new_ids = [i for i in self.df_commands['id'] if i not in existing_ids]
        if new_ids:
            new_embeddings = [self.embeddings_list[int(i)] for i in new_ids]
            new_metadatas = [self.df_commands.iloc[int(i)].to_dict() for i in new_ids]
            new_documents = [self.df_commands.iloc[int(i)]['text'] for i in new_ids]
            self.command_col.add(
                ids=new_ids,
                embeddings=new_embeddings,
                metadatas=new_metadatas,
                documents=new_documents,
            )

        print(f"✅ '{collection_name}' 컬렉션에 {len(new_ids)}개 문서 추가 완료")

    def execute_command(self, text, top_k=5, threshold=0.75, important_labels=None):
        if important_labels is None:
            important_labels = []

        query_emb = self.model.encode([text], convert_to_numpy=True)
        docs = self.command_col.query(
            query_embeddings=query_emb.tolist(),
            n_results=top_k,
            include=["documents", "metadatas", "embeddings"]
        )

        top_results = []
        executed_commands = []
        seen_labels = set()

        for db_emb, meta, doc_text in zip(docs['embeddings'][0], docs['metadatas'][0], docs['documents'][0]):
            sim_score = float(cosine_similarity(query_emb, [np.array(db_emb)])[0][0])
            label_str = meta.get('label', doc_text)
            desc_str = meta.get('description', label_str)

            if label_str in seen_labels:
                continue
            seen_labels.add(label_str)

            if sim_score < threshold and label_str not in important_labels:
                continue

            top_results.append({
                "source": "command",
                "score": sim_score,
                "label": label_str,
                "description": desc_str
            })

            print(f"실행: {label_str} -> {desc_str}")
            executed_commands.append({
                "source": "command",
                "score": sim_score,
                "label": label_str,
                "description": desc_str
            })

        if not executed_commands:
            print("실행: /NO_FUNCTION -> /NO_FUNCTION")
            executed_commands.append({
                "source": "command",
                "score": 1.0,
                "label": "/NO_FUNCTION",
                "description": "/NO_FUNCTION"
            })

        executed_commands = sorted(executed_commands, key=lambda x: x['score'], reverse=True)
        top_results = sorted(top_results, key=lambda x: x['score'], reverse=True)
        cosine_score = max([r['score'] for r in top_results], default=1.0)
        status = "MATCH" if top_results else "NO_MATCH"

        return {
            "status": status,
            "cosine_score": cosine_score,
            "top_results": top_results,
            "executed_commands": executed_commands
        }

# =========================================
# 모듈 직접 실행 - 테스트 코드
# =========================================

if __name__ == "__main__":
    searcher = CommandVectorSearch()
    examples = [
        "BGA 시작",
        "LGA 창 열기",
        "PRS 결과 확인",
        "BGA 티칭 지잆",      # 오타
        "LGA 탭 이동 테스트",
        "오늘 날씨 어때?",
        "컴퓨터 켜줘",
        "조명 화면 보기",
        "히스토리 열기",
        "PRS 결과 재티칭 시도"
    ]
    for ex in examples:
        print(f"\n입력: {ex}")
        res = searcher.execute_command(ex, top_k=3, threshold=0.85, important_labels=["/windows/teaching/prs/reteach"])
        print(res)
        print("-"*50)
