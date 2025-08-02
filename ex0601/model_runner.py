import torch
import time
from transformers import AutoModelForCausalLM, AutoTokenizer
# from prompt_combine_none_add_ex import system_prompt
# from prompt_combine_none_add_ex1 import system_prompt
from prompt_combine_none import system_prompt
# from prompt_combine import system_prompt
# from prompt_only import system_prompt
import re

def extract_assistant_response(full_text: str) -> str:
    # 1. [|assistant|] 뒤의 전체 텍스트만 가져오기
    match = re.search(r"\[\|assistant\|\](.+)", full_text, re.DOTALL)
    if not match:
        return full_text.strip()

    # 2. 해당 영역 추출
    assistant_text = match.group(1).strip()

    # 3. 코드 블록 제거 (```python ... ``` 등)
    assistant_text = re.sub(r"```(?:python)?\s*(.*?)```", r"\1", assistant_text, flags=re.DOTALL)

    # 4. 각 줄별로 정리된 함수 호출만 추출
    lines = assistant_text.splitlines()
    clean_lines = [line.strip(" `") for line in lines if line.strip()]

    return "\n".join(clean_lines)

def extract_function_calls_trillion(full_text: str) -> str:
    # 1. Trillion 스타일: 'assistant' 다음 줄부터 내용 추출
    match = re.search(r"assistant\s*\n(.+)", full_text, re.DOTALL)
    if not match:
        return full_text.strip()

    assistant_text = match.group(1).strip()

    # 2. 코드 블록 제거 (```python ... ``` 등)
    assistant_text = re.sub(r"```(?:python)?\s*(.*?)```", r"\1", assistant_text, flags=re.DOTALL)

    # 3. 줄별로 함수 호출만 추출
    lines = assistant_text.splitlines()
    pattern = r"^[a-zA-Z_][a-zA-Z0-9_]*\s*\(.*?\)$"  # 함수명(인자) 형태
    clean_lines = [line.strip(" `\"'") for line in lines if re.match(pattern, line.strip(" `\"'"))]

    return "\n".join(clean_lines)

# def extract_assistant_response(text: str) -> str:
#     match = re.search(r"\[\|assistant\|\](.+)", text, re.DOTALL)
#     if match:
#         assistant_text = match.group(1).strip()
#     else:
#         match2 = re.search(r"assistant\s*\n(.+)", text, re.DOTALL)
#         if match2:
#             assistant_text = match2.group(1).strip()
#         else:
#             assistant_text = text.strip()
#     assistant_text = assistant_text.strip(" `")
#     pattern = r"[a-zA-Z_]+\([^\)]*\)"
#     calls = re.findall(pattern, assistant_text)
#     return "\n".join(calls) if calls else ""

model_name = "LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct"
#model_name = "trillionlabs/Trillion-7B-preview"
#model_name = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    trust_remote_code=True
).to("cuda")

tokenizer = AutoTokenizer.from_pretrained(model_name)


def get_gpu_memory():
    allocated_mb = torch.cuda.memory_allocated() / 1024**2
    reserved_mb = torch.cuda.memory_reserved() / 1024**2
    return round(allocated_mb, 2), round(reserved_mb, 2)


def run_model(text, system_prompt=""):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text}
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
   
    
    
    if model_name == "trillionlabs/Trillion-7B-preview":
        assistant_only = extract_function_calls_trillion(decoded_output)
    else:
        assistant_only = extract_assistant_response(decoded_output)
    
    if not assistant_only.strip():
        assistant_only = "NO_FUNCTION"
    
    allocated, reserved = get_gpu_memory() 

    return {
        "output": assistant_only,
        "elapsed_time": elapsed_time,
        "gpu_memory": {
            "allocated_mb": allocated,
            "reserved_mb": reserved
        }
    }

