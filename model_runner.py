import torch
import time
from transformers import AutoModelForCausalLM, AutoTokenizer
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

# 현재 사용 가능한 장치 설정 (GPU 사용 가능 여부 확인)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# 기본 모델 이름 설정
DEFAULT_MODEL_NAME = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"

# 모델 사전 로드 정보 출력
print(f"[INFO] Preloading model: {DEFAULT_MODEL_NAME}")
# 모델과 토크나이저 로드
current_model = AutoModelForCausalLM.from_pretrained(
    DEFAULT_MODEL_NAME,
    revision="c38726a",
    torch_dtype=torch.bfloat16,
    trust_remote_code=True,
    device_map="auto"
)
current_tokenizer = AutoTokenizer.from_pretrained(DEFAULT_MODEL_NAME)
current_model_name = DEFAULT_MODEL_NAME

def extract_assistant_response(text: str) -> str:
    """
    LLM의 응답에서 assistant의 텍스트를 추출하는 함수.
    
    Args:
        text (str): LLM의 전체 응답 텍스트.
    
    Returns:
        str: assistant의 응답 텍스트.
    """
    # 정규 표현식을 사용하여 assistant의 응답 부분을 찾음
    match = re.search(r"\[\|assistant\|\](.+)", text, re.DOTALL)
    if match:
        assistant_text = match.group(1).strip()
    else:
        match2 = re.search(r"assistant\s*\n(.+)", text, re.DOTALL)
        if match2:
            assistant_text = match2.group(1).strip()
        else:
            assistant_text = text.strip()
    # 불필요한 공백 및 기호 제거
    assistant_text = assistant_text.strip(" `")
    # 함수 호출 패턴을 찾음
    pattern = r"[a-zA-Z_]+\([^\)]*\)"
    calls = re.findall(pattern, assistant_text)
    return "\n".join(calls) if calls else ""

def get_gpu_memory():
    """
    현재 GPU 메모리 사용량을 반환하는 함수.
    
    Returns:
        tuple: (할당된 메모리, 예약된 메모리) 단위는 MB.
    """
    if not torch.cuda.is_available():
        return 0.0, 0.0
    
    allocated_mb = torch.cuda.memory_allocated() / 1024**2
    reserved_mb = torch.cuda.memory_reserved() / 1024**2
    return round(allocated_mb, 2), round(reserved_mb, 2)

def switch_model(new_model_name: str):
    """
    기존 모델/토크나이저를 언로드하고 새 모델을 로드하는 함수.
    
    Args:
        new_model_name (str): 로드할 새 모델의 이름.
    
    Returns:
        dict: 모델 로드 상태 및 메모리 정보.
    """
    global current_model, current_tokenizer, current_model_name

    if not new_model_name:
        raise ValueError("model_name is required")

    # 현재 모델과 새 모델이 같으면 재사용
    if current_model_name == new_model_name:
        allocated, reserved = get_gpu_memory()
        return {
            "status": "reused",
            "model_name": current_model_name,
            "hf_device_map": getattr(current_model, "hf_device_map", None),
            "gpu_memory": {"allocated_mb": allocated, "reserved_mb": reserved},
        }

    print(f"[INFO] Switching model: {current_model_name} -> {new_model_name}")

    try:
        # 기존 모델과 토크나이저 삭제
        if current_model is not None:
            del current_model
        if current_tokenizer is not None:
            del current_tokenizer
    finally:
        # 가비지 컬렉션 및 GPU 캐시 비우기
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # 새 모델과 토크나이저 로드
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

# CSV 로그 파일 경로 설정
CSV_LOG_PATH = "model_logs.csv"

def log_to_csv(user_input, current_window_info, llm_output, System_prompt):
    """
    사용자 입력 및 LLM 출력을 CSV 파일에 기록하는 함수.
    
    Args:
        user_input (str): 사용자 입력.
        current_window_info (dict): 현재 열린 창 정보.
        llm_output (str): LLM의 출력.
        System_prompt (str): 사용된 시스템 프롬프트.
    """
    file_exists = os.path.isfile(CSV_LOG_PATH)

    with open(CSV_LOG_PATH, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)

        # 파일이 존재하지 않으면 헤더 작성
        if not file_exists:
            writer.writerow(["User_input", "Current_window_info", "System_prompt", "LLM_output"])

        # 데이터 기록
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
    """
    LLM 모델을 실행하는 함수 - 복합 명령어 지원.
    
    Args:
        prompt (str): 사용자 입력 프롬프트.
        current_window_info (dict): 현재 열린 창 정보.
        model_name (str): 사용할 모델 이름.
    
    Returns:
        dict: LLM의 출력, 경과 시간, GPU 메모리 정보.
    """
    global current_model, current_tokenizer, current_model_name

    # Intent classifier 처리
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
    
    # 모델 로드 또는 재사용
    if model_name != current_model_name:
        print(f"[INFO] Loading model: {model_name}")
        current_model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
            device_map="auto"
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
        {"role": "user", "content": f"{prompt}\n\n[Gvision current_opened_window_and_tab]\n{current_window_info}"}
    ]

    # 입력 ID 생성
    input_ids = current_tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to(DEVICE)

    # max_new_tokens 증가 (복합 명령어 지원)
    output = current_model.generate(
        input_ids,
        eos_token_id=current_tokenizer.eos_token_id,
        max_new_tokens=200,  # 100 → 200
        do_sample=False
    )
    end = time.time()
    elapsed_time = round(end - start, 5)

    # 출력 디코딩
    decoded_output = current_tokenizer.decode(output[0], skip_special_tokens=True)

    # EXAONE vs Qwen 파서 분리
    is_exaone = "EXAONE" in current_model_name or "exaone" in current_model_name.lower()

    if is_exaone:
        # EXAONE: 복합 명령 모두 추출 (assistant 블록 전체 사용)
        try:
            assistant_only = decoded_output.split('[|assistant|]')[1].strip()
        except:
            assistant_only = decoded_output.strip()   # fallback
    else:
        # Qwen / ChatML fallback: 슬래시(/)로 시작하는 줄만 API로 인식
        lines = decoded_output.strip().split("\n")
        api_candidates = [line.strip() for line in lines if line.strip().startswith("/")]
        assistant_only = "\n".join(api_candidates) if api_candidates else "/NO_FUNCTION"

   # EXAONE 백틱 제거 
    assistant_only = assistant_only.replace("```", "").strip()
    assistant_only = assistant_only.replace("`", "").strip()

    print(f"[LLM Output]\n{assistant_only}")
    
    allocated, reserved = get_gpu_memory()

    # 로그 기록
    log_to_csv(prompt, current_window_info, assistant_only, selected_key)
    
    return {
        "output": assistant_only,
        "elapsed_time": elapsed_time,
        "gpu_memory": {
            "allocated_mb": allocated,
            "reserved_mb": reserved
        }
    }