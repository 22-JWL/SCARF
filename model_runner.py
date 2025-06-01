import torch
import time
from transformers import AutoModelForCausalLM, AutoTokenizer
from prompt_combine import system_prompt
# from prompt_only import system_prompt
from intent_classifier import classify_text 
import re

#model_name = "LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct"
#model_name = "trillionlabs/Trillion-7B-preview"
#model_name = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"
#model_name = "distilbert-base-multilingual-cased"



def extract_assistant_response(text: str) -> str:
    # 1. [|assistant|] 마커가 있으면 그 뒤 텍스트만 추출
    match = re.search(r"\[\|assistant\|\](.+)", text, re.DOTALL)
    if match:
        assistant_text = match.group(1).strip()
    else:
        # 2. 없으면 'assistant'로 시작하는 줄 뒤 텍스트 추출
        match2 = re.search(r"assistant\s*\n(.+)", text, re.DOTALL)
        if match2:
            assistant_text = match2.group(1).strip()
        else:
            # 3. 둘 다 없으면 전체 텍스트 사용 (fallback)
            assistant_text = text.strip()
    # 4. 백틱/공백 제거
    assistant_text = assistant_text.strip(" `")
    # 5. 함수 호출 패턴 추출
    pattern = r"[a-zA-Z_]+\([^\)]*\)"
    calls = re.findall(pattern, assistant_text)
    return "\n".join(calls) if calls else ""



#승택_exaone만 해당하는 파싱함수
# def extract_assistant_response(full_text: str) -> str:
#     # 1. [|assistant|] 뒤의 전체 텍스트만 가져오기
#     match = re.search(r"\[\|assistant\|\](.+)", full_text, re.DOTALL)
#     if not match:
#      return full_text.strip()

#     # 2. 해당 영역에서 함수 호출 라인들만 정제
#     assistant_text = match.group(1).strip()

#     # 3. 각 줄별로 정리된 함수 호출만 추출
#     lines = assistant_text.splitlines()
#     clean_lines = [line.strip(" `") for line in lines if line.strip()]

#     return "\n".join(clean_lines)

#2. 함수는 다 추출
# def extract_assistant_response(full_text: str) -> str:
#     pattern = r"[a-zA-Z_]+\([^\)]*\)"
#     matches = re.findall(pattern, full_text)
#     if matches:
#         return "\n".join(matches)
#     else:
#         return ""



def get_gpu_memory():
    allocated_mb = torch.cuda.memory_allocated() / 1024**2
    reserved_mb = torch.cuda.memory_reserved() / 1024**2
    return round(allocated_mb, 2), round(reserved_mb, 2)


def run_model(prompt: str ,model_name: str):
    if model_name == "distilbert-base-multilingual-cased":
        # intent_classifier의 classify_text 함수 활용
        result = classify_text(prompt)
        # LLM 결과와 동일한 포맷으로 반환
        return {
            "output": result["label"],
            "elapsed_time": 0.0,
            "gpu_memory": {
                "allocated_mb": 0.0,
                "reserved_mb": 0.0
            }
        }
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True
    ).to("cuda")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    input_ids = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to("cuda")

    start = time.time()

    output = model.generate(
        input_ids,
        eos_token_id=tokenizer.eos_token_id,
        max_new_tokens=100,
        do_sample=False
    )

    end = time.time()
    elapsed_time = round(end - start, 5)

    decoded_output = tokenizer.decode(output[0], skip_special_tokens=True)
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

