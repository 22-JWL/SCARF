import torch
from basic_prompt import system_prompt
from slot_filling import system_prompt as slot_prompt
from router import router_prompt
import json
# 현재 사용 가능한 장치 설정 (GPU 사용 가능 여부 확인)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

slotJson = "slot.json"
def load_slot():
    with open(slotJson, "r", encoding="utf-8") as f:
        return json.load(f)

def save_slot(slot_state):
    with open(slotJson, "w", encoding="utf-8") as f:
        json.dump(slot_state, f, ensure_ascii=False, indent=2)

def update_slot_from_llm(llm_output: dict):
    """
    llm_output = {
        "update": {"value": "20", "windowName": "lga"},
        "missing": ["PropertyType"]
    }
    """
    slot_state = load_slot()

    # 1. slots 업데이트
    for key, value in llm_output.get("update", {}).items():
        if key in slot_state["slots"]:
            slot_state["slots"][key] = value
        elif key in slot_state["required"]:
            slot_state["required"][key] = value
        elif key == "action":
            slot_state["action"] = value

    # 2. missing에 따라 question 채우기
    # for missing_key in llm_output.get("missing", []):
    #     if missing_key in slot_state["required"]:
    #         if missing_key == "windowName":
    #             slot_state["question"][missing_key] = "어떤 창(windowName)을 열겠나요?"
    #         elif missing_key == "PropertyType":
    #             slot_state["question"][missing_key] = "어떤 속성 종류(PropertyType)를 변경하시나요?"

    # 3. 저장
    save_slot(slot_state)


    return slot_state

def is_required_filled(slot_state: dict) -> bool:
    """
    action에 따라 required 필드가 모두 채워졌는지 확인

    - openWindow: windowName만 필요
    - updateValue: windowName + PropertyType 필요
    - 그 외(action이 elseVaguePrompt 등): required 체크 안 함
    """
    if not slot_state or "required" not in slot_state:
        return False

    action = slot_state.get("action", "")
    
    if action == "openWindow":
        #  selected_key, system_prompt_selected
        return bool(slot_state["required"].get("windowName"))
        
    
    elif action == "updateValue":
        return all([
            slot_state["required"].get("windowName"),
            slot_state["required"].get("PropertyType")
        ])
    else:  # vaguePrompt 등 그 외
        return True

def fill_question_from_required(slot_state):
    """
    required에서 비어 있는 항목을 찾아
    같은 key를 question에 "" 로 넣는다.
    """

    required = slot_state.get("required", {})
    question = slot_state.get("question", {})

    for key, value in required.items():
        if not value:  # 값이 비어 있으면
            question[key] = ""  # question에 key 생성

    slot_state["question"] = question
    return slot_state

# 슬롯 채우기 
def slot_fill_intent(prompt: str, model, tokenizer) -> str:

    messages = [
        {"role": "system", "content": slot_prompt},
        {"role": "user", "content": prompt}
    ]

    # while is_required_filled() is False:  # 슬롯의 요구되는 부분이 다 채워질 때까지 반복
        # slot filling 실행
    input_ids = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to(DEVICE)

    # 모델 생성
    output = model.generate(
        input_ids,
        eos_token_id=tokenizer.eos_token_id,
        max_new_tokens=100, 
        do_sample=False
    )

    # 디코딩
    decoded = tokenizer.decode(output[0], skip_special_tokens=True)
    # assistant 부분만 추출
    slot_llm_output = decoded.split('[|assistant|]')[-1].strip()
    print(f"[slot_fill_intent]\n{slot_llm_output}")
    # if is_required_filled(update_slot_from_llm(slot_llm_output)):   # 받은 내용 토대로 슬롯 업데이트하고 슬롯찼는지 확인
    #     return filter_system_prompt(slotJson["required"].get("windowName"), "")
    # else: # 아니라면 질문을 해야하는 상황...
    #     fill_question_from_required() # 이 질문을 넘길 수 잇어야함...
        # return filter_system_prompt("slotJson["required"].get("windowName")","")
         # selected_key, system_prompt_selected
    # is_required_filled
    # return filter_system_prompt(category, prompt)