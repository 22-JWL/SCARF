# rag.py
# 아래를 cmd 창에서 설치
# pip install -U langchain-community
# pip install sentence-transformers
# pip install chromadb


from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
# import rag_prompt

def create_vectorstore(file_path = "rag_prompt.py", 
                       skip_lines=7, chunk_size=1000, chunk_overlap=50, 
                       separators=["•"], 
                       model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
                       ):
    # 1. 데이터 불러오기
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    text = "".join(lines[skip_lines:])

    # 2. 청킹→ 길이가 긴 텍스트를 일정 크기로 쪼개기
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators
    )
    splits = text_splitter.split_text(text)

    # 3. 임베딩→ 쪼갠 텍스트를 벡터로 변환
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": False}
    )

    # 4. 벡터스토어 생성
    vectorstore = Chroma.from_texts(splits, embedding=embeddings)
    return vectorstore

def query_vectorstore(vectorstore, query, top_k=2):
    # 5. 질문 → 유사도 검색
    results = vectorstore.similarity_search(query, k=top_k)
    
    # 중복 제거
    unique_contents = list({r.page_content for r in results})
    for r in unique_contents:
        print("유사도 검색 결과:", r)
    return unique_contents
