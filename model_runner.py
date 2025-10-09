import torch
import time
import pandas as pd
import os
from transformers import AutoModelForCausalLM, AutoTokenizer
# from prompt_combine import system_prompt
# from prompt_only import system_prompt
from prompt_combine_none import system_prompt
from intent_classifier import classify_text 
from rag import create_vectorstore, query_vectorstore
import re
import gc

#model_name = "LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct"
#model_name = "trillionlabs/Trillion-7B-preview"
#model_name = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"
#model_name = "distilbert-base-multilingual-cased"
#model_name = "Qwen/Qwen3-0.6B"


DEFAULT_MODEL_NAME = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"

print(f"[INFO] Preloading model: {DEFAULT_MODEL_NAME}")
current_model = AutoModelForCausalLM.from_pretrained(
    DEFAULT_MODEL_NAME,
    torch_dtype=torch.bfloat16,
    trust_remote_code=True,
    device_map="auto"   # GPU에 바로 올려
)
current_tokenizer = AutoTokenizer.from_pretrained(DEFAULT_MODEL_NAME)
current_model_name = DEFAULT_MODEL_NAME

# rag를 위한 코드...최초 1회 실행. 벡터스토어 생성...
vectorstore = create_vectorstore() # prompt_combine_none.py 를 청킹, 임베딩, 백스터화? 함
print(type(vectorstore))
print("총 문서 청킹 수:", len(vectorstore._collection.get()['metadatas']))
# vectorstore.persist() # 저장

def extract_assistant_response(text: str) -> str:
    match = re.search(r"\[\|assistant\|\](.+)", text, re.DOTALL)
    if match:
        assistant_text = match.group(1).strip()
    else:
        match2 = re.search(r"assistant\s*\n(.+)", text, re.DOTALL)
        if match2:
            assistant_text = match2.group(1).strip()
        else:
            assistant_text = text.strip()
    assistant_text = assistant_text.strip(" `")
    pattern = r"[a-zA-Z_]+\([^\)]*\)"
    calls = re.findall(pattern, assistant_text)
    return "\n".join(calls) if calls else ""


def get_gpu_memory():
    allocated_mb = torch.cuda.memory_allocated() / 1024**2
    reserved_mb = torch.cuda.memory_reserved() / 1024**2
    return round(allocated_mb, 2), round(reserved_mb, 2)

# 유저 채팅과 rag 결과 확인용...
csv_path = "rag_results.csv" 

def save_messages(messages, llm_response):
    # messages에서 role별로 content 가져오기
    system_message = next((m['content'] for m in messages if m['role'] == 'system'), "")
    user_message = next((m['content'] for m in messages if m['role'] == 'user'), "")

    # DataFrame 생성
    df = pd.DataFrame([{
        "usermessage": user_message,
        "system_message": system_message,
        "llm_response": llm_response
    }])

    # 기존 CSV가 있으면 이어서 저장
    if os.path.exists(csv_path):
        df_old = pd.read_csv(csv_path)
        df['index'] = df_old['index'].max() + 1 + df.index
        df = pd.concat([df_old, df], ignore_index=True)
    else:
        df['index'] = df.index + 1

    df = df[["index", "usermessage", "system_message", "llm_response"]]
    df.to_csv(csv_path, index=False)

# 프롬프트 앞에 가이드는 미리 저장 
with open("rag_prompt.py", "r", encoding="utf-8") as f:
    text = f.read()  # 전체 문자열
system_lines = text.splitlines()
system_prompt_head = "\n".join(system_lines[0:5])

# -----------------------------------------------------------------------------
# 모델 전환 API
# -----------------------------------------------------------------------------
def switch_model(new_model_name: str):
    """
    기존 모델/토크나이저를 언로드하고(new_model_name으로) 새 모델을 로드한다.

    - VRAM 해제 순서: del -> gc.collect() -> torch.cuda.empty_cache()
    - 로딩: device_map="auto"로 GPU 우선 적재(부족분은 CPU/디스크 오프로딩)
    - 반환: 상태, 현재 모델명, 장치 배치(hf_device_map), GPU 메모리 지표
    """
    global current_model, current_tokenizer, current_model_name

    if not new_model_name:
        raise ValueError("model_name is required")

    if current_model_name == new_model_name:
        allocated, reserved = get_gpu_memory()
        return {
            "status": "reused",
            "model_name": current_model_name,
            "hf_device_map": getattr(current_model, "hf_device_map", None),
            "gpu_memory": {"allocated_mb": allocated, "reserved_mb": reserved},
        }

    print(f"[INFO] Switching model: {current_model_name} -> {new_model_name}")

    # 1) 기존 모델 언로드 및 캐시 정리
    try:
        if current_model is not None:
            del current_model
        if current_tokenizer is not None:
            del current_tokenizer
    finally:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # 2) 새 모델 로드 (GPU 우선, 자동 오프로딩)
        current_model = AutoModelForCausalLM.from_pretrained(
            new_model_name,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
            device_map="auto",
        )
        current_tokenizer = AutoTokenizer.from_pretrained(new_model_name)
        current_model_name = new_model_name

        allocated, reserved = get_gpu_memory()
        return {
            "status": "loaded",
            "model_name": current_model_name,
            "hf_device_map": getattr(current_model, "hf_device_map", None),
            "gpu_memory": {"allocated_mb": allocated, "reserved_mb": reserved},
        }

def run_model(prompt: str, model_name: str):
    global current_model, current_tokenizer, current_model_name

   
    # 분기 처리 - intent classifier는 별도 처리
    if model_name == "distilbert-base-multilingual-cased":
        result = classify_text(prompt)
        return {
            "output": result["label"],
            "elapsed_time": 0.0,
            "gpu_memory": {
                "allocated_mb": 0.0,
                "reserved_mb": 0.0
            }
        }
    
    #다른 모델 교체되면 동적으로 로드
    if model_name != current_model_name:
        print(f"[INFO] Loading model: {model_name}")
        current_model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
            device_map="auto"  # GPU에 올림
        )
        current_tokenizer = AutoTokenizer.from_pretrained(model_name)
        current_model_name = model_name
    else:
        print(f"[INFO] Reusing model: {model_name}")



     # 추론 실행
    start = time.time()

    system_prompt_rag = query_vectorstore(vectorstore, prompt)
    system_prompt_rag_str = " ".join(system_prompt_rag)
    # 프롬프트 구성
    messages = [
        {"role": "system", "content": system_prompt_head + system_prompt_rag_str},  # system_prompt 원래 코드...
        {"role": "user", "content": prompt}
    ]

    input_ids = current_tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to("cuda")

    output = current_model.generate(
        input_ids,
        eos_token_id=current_tokenizer.eos_token_id,
        max_new_tokens=100,
        do_sample=False
    )
    end = time.time()
    elapsed_time = round(end - start, 5)

    decoded_output = current_tokenizer.decode(output[0], skip_special_tokens=True)
    #assistant_only = extract_assistant_response(decoded_output)
    assistant_only = decoded_output.split('[|assistant|]')[1].strip().strip("\n").strip("`")
    print(assistant_only)
    save_messages(messages, assistant_only)  # rag 결과를 llm 답변과 함께 저장
    allocated, reserved = get_gpu_memory()

    return {
        "output": assistant_only,
        "elapsed_time": elapsed_time,
        "gpu_memory": {
            "allocated_mb": allocated,
            "reserved_mb": reserved
        }
    }

