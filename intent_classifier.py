import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

id2label = {                                                    # 라벨 ID -> 라벨 이름 : 매핑 도메인에 맞는 의미 있는 문자열로 변환하기 위한 매핑 테이블.
    "LABEL_0": "open_teaching",
    "LABEL_1": "inspection_window",
    "LABEL_2": "start_inspection",
    "LABEL_3": "calibration",
    "LABEL_4": "setting",
    "LABEL_5": "change_recipe"
}



DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "result", "checkpoint-40")                    # 파인튜닝된 intent 분류 모델이 저장된 로컬 디렉토리
DEFAULT_TOKENIZER_NAME = "distilbert-base-multilingual-cased"   # 사용할 사전 학습 토크나이저 이름(HF Hub 상의 모델 이름)

def classify_text(                                              # 분류 함수
    text: str,
    model_dir: str = DEFAULT_MODEL_DIR,
    tokenizer_name: str = DEFAULT_TOKENIZER_NAME
) -> dict:
    """
    입력 텍스트를 받아 intent 라벨과 신뢰도(score)를 반환합니다.
    - text: 분류할 사용자 자연어 명령어
    - model_dir: 로드할 분류 모델이 저장된 디렉토리 (HF from_pretrained 형식)
    - tokenizer_name: 사용할 토크나이저 이름 (HF Hub 또는 로컬 경로)
    반환:
        {
            "label": (매핑된 도메인 라벨 문자열),
            "score": (0~1 사이의 예측 확률)
        }
    """

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)                   # 텍스트를 토큰 ID 시퀀스로 변환
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)       # 사전 학습된 시퀀스 분류 모델 로드

  
    classifier = pipeline("text-classification", model=model, tokenizer=tokenizer, device=0)      # 파이프라인 생성("text-classification" → 시퀀스 분류용 파이프라인 생성)

    result = classifier(text)[0]                                                 # 예측 결과 추출 : classifier(text)는 리스트 형태로 결과를 반환하므로 첫 번째 요소만 사용

    label = id2label.get(result["label"], result["label"])                       # 라벨 ID를 도메인 라벨 문자열로 매핑                 
   
    score = round(result["score"], 4)                                            # score를 소수점 4자리까지 반올림


    return {
        "label": label,                                                          # 최종 결과를 딕셔너리로 반환
        "score": score
    }
