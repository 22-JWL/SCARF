import torch
import time
import json
from transformers import AutoModelForCausalLM, AutoTokenizer
# from prompt_combine import system_prompt
# from prompt_only import system_prompt
from prompt_combine_none import system_prompt
from prompt_classify_by_windows.bga import system_prompt as bga_prompt
from prompt_classify_by_windows.lga import system_prompt as lga_prompt
from prompt_classify_by_windows.qfn import system_prompt as qfn_prompt
from prompt_classify_by_windows.mapping import system_prompt as mapping_prompt
from prompt_classify_by_windows.calibration import system_prompt as calibration_prompt
from prompt_classify_by_windows.light import system_prompt as light_prompt
from prompt_classify_by_windows.history import system_prompt as history_prompt
from prompt_classify_by_windows.strip import system_prompt as strip_prompt
from prompt_classify_by_windows.settings import system_prompt as settings_prompt
from prompt_classify_by_windows.confirmLog import system_prompt as confirmLog_prompt
from intent_classifier import classify_text 
import re
import gc
import csv
import os

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

CSV_LOG_PATH = "model_logs.csv"   # 기록 저장 파일

def log_to_csv(user_input,current_window_info, llm_output, System_prompt):
    """user_input, result 를 CSV 파일에 누적 저장"""
    file_exists = os.path.isfile(CSV_LOG_PATH)

    with open(CSV_LOG_PATH, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)

        # 파일이 처음 생성될 때 헤더 추가
        if not file_exists:
            writer.writerow(["User_input", "Current_window_info", "System_prompt", "LLM_output"])

        writer.writerow([
            user_input,
            current_window_info,
            System_prompt,
            llm_output
        ])

def filter_system_prompt(current_window_info: str, prompt: str) -> str:
    info = current_window_info.lower()

    mapping = {
        "bga": bga_prompt,
        "lga": lga_prompt,
        "qfn": qfn_prompt,
        "mapping": mapping_prompt,
        "strip": strip_prompt,
        "light": light_prompt,
        "calibration": calibration_prompt,
        "history": history_prompt,
        "settings": settings_prompt,
        "": system_prompt
    }

    matched_keys = []
    matched_prompts = []

# 2. confirmLog 체크: 최근 메시지에서 system이 확인 메시지 보냈는지 확인
    if "해당 명령을 실행할까요?" in prompt:  # contain만 확인
        print("[INFO] confirmLog prompt matched.")
        matched_prompts = [confirmLog_prompt]  # 덮어쓰기
        matched_keys.append("confirmLog")
        return ["confirmLog"], confirmLog_prompt

    for key, prompt in mapping.items():
        if key and key in info:  # 빈 문자열("")은 제외
            matched_keys.append(key)
            matched_prompts.append(prompt)

    # 아무것도 매칭되지 않으면 기본 시스템 프롬프트 사용
    if not matched_prompts:
        return [], system_prompt

    # 여러 개의 창 프롬프트를 하나로 결합 (공백이나 구분자 포함)
    combined_prompt = "\n\n".join(matched_prompts)

    return matched_keys, combined_prompt

def run_model(prompt: str, current_window_info: dict, model_name: str):
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
    selected_key, system_prompt_selected = filter_system_prompt(" ".join(current_window_info.keys()),prompt)
    messages = [
        {"role": "system", "content": system_prompt_selected},
        {"role": "user", "content": f"{prompt}\n\n[Gvision Current Info]\n{current_window_info}"}
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

    log_to_csv(prompt, current_window_info, assistant_only,selected_key) # 기록
    return {
        "output": assistant_only,
        "elapsed_time": elapsed_time,
        "gpu_memory": {
            "allocated_mb": allocated,
            "reserved_mb": reserved
        }
    }
