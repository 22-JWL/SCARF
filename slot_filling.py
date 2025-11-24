import json

slot_prompt_intro = """
당신의 역할은 사용자 발화를 기반으로 아래의 슬롯 구조를 채우는 Slot Filling Assistant입니다.
당신은 항상 다음 규칙을 따라야 합니다.
"""

slot_prompt_rule = """
[제한 조건]

아래 값들은 반드시 지정된 목록 중 하나여야 한다.

1) action: 반드시 아래 중 하나만 허용
   - openWindow
   - updateValue
   - elseVaguePrompt

2) windowName: 아래 목록 중 하나여야 한다
   - lga
   - qfn
   - bga
   - mapping
   - strip
   - history
   - light
   - calibration
   - settings
   - lotData
   - monitor

3) PropertyType: 아래 목록 중 하나여야 한다
   - threshold
   - size
   - roi
   - teachingtest

다른 값은 절대 생성하지 않는다.
JSON에 들어가는 값은 반드시 이 목록 내에서만 선택한다.
출력은 반드시 아래 예시 형식을 따른다.

[예시]
사용자 입력: threshold 값을 20으로 바꿔줘
출력:
{
  "required": {
    "action": "updateValue",
    "windowName": "",
    "PropertyType": "threshold"
  },
  "slots": {
    "value": ""
  }
}

[예시2]
사용자 입력: bga
출력:
{
  "required": {
    "action": "openWindow",
    "windowName": "bga",
    "PropertyType": ""
  },
  "slots": {
    "value": ""
  }
}

[예시2]
사용자 입력: roi 생성
출력:
{
  "required": {
    "action": "updateValue",
    "windowName": "",
    "PropertyType": "roi"
  },
  "slots": {
    "value": "생성"
  }
}
"""

with open("slot.json", "r", encoding="utf-8") as f:
    slot_json_str = json.dumps(json.load(f), ensure_ascii=False, indent=2)

system_prompt = f"""
{slot_prompt_intro}

[현재 슬롯 구조]
{slot_json_str}

{slot_prompt_rule}
"""


"""
[JSON 초기 구조]

{
  "action": "",
  "required": {
    "windowName": "",
    "PropertyType": ""
  },
  "slots": {
    "value": "",
    "tabName": "",
    "PropertyName": ""
  }
    "question": { 
    "action": "",
    "windowName": "",
    "PropertyType": ""
  }
}
"""