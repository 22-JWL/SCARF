import torch
import time
from transformers import AutoModelForCausalLM, AutoTokenizer
# from prompt_combine import system_prompt
# from prompt_only import system_prompt
from prompt_combine_none import system_prompt
from intent_classifier import classify_text 
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
    
# 벡터 기반 유사도 판별 함수 -> 유사도 기준 높으면 바로 처리, 아니면 LLM으로 처리
def hybrid_command_or_llm(
    user_input, 
    vector_searcher, 
    sim_threshold=0.7,  # 0.8 → 0.7로 조정
    top_k=3, 
    llm_model_name=DEFAULT_MODEL_NAME
):
    vec_res = vector_searcher.execute_command(user_input, top_k=top_k, threshold=sim_threshold)
    top_score = vec_res.get('cosine_score', 0.0)
    top_cmd = vec_res['executed_commands'][0] if vec_res['executed_commands'] else None
    top_label = top_cmd['label'] if top_cmd else None
    status = vec_res.get('status', 'NO_MATCH')

    # ✅ 여기 조건문을 이렇게 명확하게 구분
    if status == "MATCH" and top_score >= sim_threshold and top_label and top_label != "/NO_FUNCTION":
        print(f"\n[임베딩 우선] 입력 '{user_input}' → '{top_label}' (score: {top_score:.2f})")
        result = {
            "step": "vector_match",
            "executed_command": top_cmd,
            "vector_result": vec_res
        }
    else:
        print(f"\n[LLM Fallback] 벡터DB 미매칭 또는 유사도 부족 ({top_score:.2f}, status={status}, label={top_label}) → LLM 실행")
        llm_res = run_model(user_input, llm_model_name)
        result = {
            "step": "llm_fallback",
            "llm_result": llm_res,
            "vector_result": vec_res
        }

    return result


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
    
    # 프롬프트 구성
    messages = [
        {"role": "system", "content": system_prompt},
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
    allocated, reserved = get_gpu_memory()

    return {
        "output": assistant_only,
        "elapsed_time": elapsed_time,
        "gpu_memory": {
            "allocated_mb": allocated,
            "reserved_mb": reserved
        }
    }