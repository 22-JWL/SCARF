import torch
import time
from transformers import AutoModelForCausalLM, AutoTokenizer
# from prompt_combine import system_prompt
# from prompt_only import system_prompt
from prompt_combine_none import system_prompt
from intent_classifier import classify_text 
import re

#model_name = "LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct"
#model_name = "trillionlabs/Trillion-7B-preview"
#model_name = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"
#model_name = "distilbert-base-multilingual-cased"

# 전역 캐시
current_model = None
current_tokenizer = None
current_model_name = None


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


def run_model(prompt: str, model_name: str):
    global current_model, current_tokenizer, current_model_name

    # 추론 실행
    start = time.time()
    
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

    # 모델 캐시 확인
    if current_model is None or current_model_name != model_name:
        print(f"[INFO] Loading model: {model_name}")
        current_model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True
        ).to("cuda")
        current_tokenizer = AutoTokenizer.from_pretrained(model_name)
        current_model_name = model_name
    else:
        print(f"[INFO] Reusing model: {model_name}")

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
    assistant_only = extract_assistant_response(decoded_output)
    allocated, reserved = get_gpu_memory()

    return {
        "output": assistant_only,
        "elapsed_time": elapsed_time,
        "gpu_memory": {
            "allocated_mb": allocated,
            "reserved_mb": reserved
        }
    }
