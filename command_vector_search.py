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
        embedding_model_name='paraphrase-multilingual-MiniLM-L12-v2',
        force_reload=False,
    ):
        # print("CSV 파일 존재 및 경로 확인:", csv_path)

        # 1. DB/모델 로드
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.command_col = self.client.get_or_create_collection(collection_name)
        self.df_commands = pd.read_csv(csv_path)
        self.df_commands['id'] = self.df_commands.index.astype(str)

        # 2. 임베딩
        self.model = SentenceTransformer(embedding_model_name)
        self.embeddings_list = self.model.encode(
            self.df_commands['text'].tolist(),
            show_progress_bar=True
        ).tolist()
        # print("임베딩 벡터 shape 예시:", np.array(self.embeddings_list[0]).shape)

        # 3. 벡터DB 동기화 (중복 제외 or 강제 리셋)
        if force_reload:
            # print("⚠️ 기존 컬렉션 전체 삭제 (force_reload=True)")
            self.command_col.delete(where={})

        try:
            existing_docs = self.command_col.get(ids=None, include=['ids'])
            existing_ids = set(existing_docs['ids'])
            # print("ChromaDB docs 수:", len(existing_ids))
        except Exception as e:
            # print("기존 컬렉션 로드 실패:", e)
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
                documents=new_documents
            )
        #     print(f"✅ {len(new_ids)}개 새 명령어 추가 완료")

        # print("명령어 shape:", self.df_commands.shape)
        # print("명령어 헤드:", self.df_commands.head())
        # print("text 컬럼 존재:", 'text' in self.df_commands.columns)

    # ============================
    # 명령 실행 함수
    # ============================
    def execute_command(self, text, top_k=5, threshold=0.2, important_labels=None, fallback_label="/NO_FUNCTION"):
        if important_labels is None:
            important_labels = []

        query_emb = self.model.encode([text], convert_to_numpy=True)
        docs = self.command_col.query(
            query_embeddings=query_emb.tolist(),
            n_results=top_k,
            include=["documents", "metadatas", "embeddings"]
        )

        top_results, executed_commands, seen_labels = [], [], set()

        for db_emb, meta, doc_text in zip(docs['embeddings'][0], docs['metadatas'][0], docs['documents'][0]):
            sim_score = float(cosine_similarity(query_emb, [np.array(db_emb)])[0][0])
            print(f"sim_score({doc_text}): {sim_score:.4f}")

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

        # fallback 처리
        if not executed_commands:
            executed_commands.append({
                "source": "command",
                "score": 1.0,
                "label": fallback_label,
                "description": fallback_label
            })
            top_results.append({
                "source": "command",
                "score": 1.0,
                "label": fallback_label,
                "description": fallback_label
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


# # ============================
# # 단독 실행 테스트
# # ============================
# if __name__ == "__main__":
#     searcher = CommandVectorSearch(
#         csv_path="all_commands.csv",
#         chroma_path="./chroma_db",
#         collection_name="commands",
#         embedding_model_name='paraphrase-multilingual-MiniLM-L12-v2',
#         force_reload=False
#     )

#     test_queries = [
#         "BGA 티칭 시작",
#         "lighting 화면 열기",
#         "히스토리 보여줘",
#         "PRS 결과 재티칭",
#         "LGA 창 켜"
#     ]

#     for idx, q in enumerate(test_queries):
#         print(f"\n=== 테스트 {idx+1}: '{q}' ===")
#         result = searcher.execute_command(q, top_k=5, threshold=0.2)
#         print("status:", result["status"])
#         print("cosine_score:", result["cosine_score"])
#         print("Top Results:")
#         for r in result["top_results"]:
#             print(f"  - label: {r['label']} / score: {r['score']:.4f}")
#         print("Executed Commands:")
#         for r in result["executed_commands"]:
#             print(f"  - label: {r['label']} / score: {r['score']:.4f}")
#         print("-" * 40)
