from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

# 라벨 ID -> 라벨 이름 매핑
id2label = {
    "LABEL_0": "open_teaching",
    "LABEL_1": "inspection_window",
    "LABEL_2": "start_inspection",
    "LABEL_3": "calibration",
    "LABEL_4": "setting",
    "LABEL_5": "change_recipe"
}

# 기본 분류 모델 경로 및 토크나이저 이름
DEFAULT_MODEL_DIR = "./result/checkpoint-40"
DEFAULT_TOKENIZER_NAME = "distilbert-base-multilingual-cased"

def classify_text(
    text: str,
    model_dir: str = DEFAULT_MODEL_DIR,
    tokenizer_name: str = DEFAULT_TOKENIZER_NAME
) -> dict:
    """
    입력 텍스트를 받아 intent 라벨과 신뢰도(score)를 반환합니다.
    """
    # 토크나이저와 모델 로드
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    # 파이프라인 생성
    classifier = pipeline("text-classification", model=model, tokenizer=tokenizer, device=0)
    # 예측
    result = classifier(text)[0]
    # 라벨 변환 및 score 추출
    label = id2label.get(result["label"], result["label"])
    score = round(result["score"], 4)
    return {
        "label": label,
        "score": score
    }
