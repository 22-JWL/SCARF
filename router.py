import torch
import torch.nn.functional as F
from collections import Counter
from setfit import SetFitModel
import os

# 설정
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MC_SAMPLES = 20
CONFIDENCE_THRESHOLD = 0.8

# 라벨 정의
ID2LABEL = {
    0: "SINGLE_QUESTION",       # 단일 질문
    1: "COMPLEX_ANALYSIS",   # 복합 분석 (SLLM 필요)
    2: "OUT_OF_SCOPE"        # 도메인 밖
}
LABEL2ID = {v: k for k, v in ID2LABEL.items()}

class UncertaintyRouter:
    """
    MC Dropout을 사용한 불확실성 기반 라우터
    """
    def __init__(self, model_path):
        self.device = DEVICE

        print(f"[Router] Loading SetFit Model from: {model_path}")

        # SetFit 모델 로드
        self.model = SetFitModel.from_pretrained(model_path).to(self.device)
        print(f"[Router] Model loaded successfully on {self.device}")

    def predict_mc_dropout(self, text):
        """
        MC Dropout을 사용한 예측
        논문 방식: dropout across hidden and attention layers in the backbone
        """
        # 1. 텍스트 토큰화
        inputs = self.model.model_body.tokenizer(
            [text],
            padding=True,
            truncation=True,
            return_tensors="pt"
        ).to(self.device)

        # 2. Body와 Head를 Train 모드로 전환 (Dropout 활성화)
        self.model.model_body.train()
        self.model.model_head.train()

        predictions = []

        # Gradients는 계산하지 않되, Dropout은 켜둔 상태로 루프
        with torch.no_grad():
            for _ in range(MC_SAMPLES):
                # A. Body 통과 (매번 다른 Dropout 마스크 적용)
                features = self.model.model_body(inputs)
                embeddings = features['sentence_embedding']

                # B. Head 통과
                outputs = self.model.model_head(embeddings)

                # 튜플 처리
                if isinstance(outputs, tuple):
                    logits = outputs[0]
                else:
                    logits = outputs

                # C. 결과 저장
                probs = torch.softmax(logits, dim=-1)
                pred_label = torch.argmax(probs, dim=-1).item()
                predictions.append(pred_label)

        # 3. 추론 후 Eval 모드로 복귀
        self.model.model_body.eval()
        self.model.model_head.eval()

        return predictions

    def check_uncertainty(self, predictions):
        """
        불확실성 판단
        """
        counts = Counter(predictions)

        # 가장 많이 예측된 라벨 찾기
        if not counts:
             return {"is_uncertain": True, "final_label": None}

        most_common_label, frequency = counts.most_common(1)[0]
        agreement_ratio = frequency / len(predictions)

        # 설정된 임계값보다 일치율이 낮으면 '불확실'로 판단
        is_uncertain = agreement_ratio < CONFIDENCE_THRESHOLD

        return {
            "is_uncertain": is_uncertain,
            "final_label_id": most_common_label,
            "final_label": ID2LABEL[most_common_label],
            "agreement_ratio": agreement_ratio,
            "raw_predictions": predictions
        }

    def route_query(self, text):
        """
        쿼리를 라우팅하는 메인 함수

        Returns:
            dict: {
                "should_use_llm": bool,  # True면 LLM 사용, False면 거절
                "reason": str,           # 라우팅 이유
                "label": str,            # 예측된 라벨
                "confidence": float      # 신뢰도
            }
        """
        # MC Dropout 예측
        predictions = self.predict_mc_dropout(text)
        result = self.check_uncertainty(predictions)

        # Case 1: OOS (도메인 밖) -> 즉시 거절
        if result["final_label_id"] == 2:
            return {
                "should_use_llm": False,
                "reason": "OUT_OF_SCOPE",
                "label": result["final_label"],
                "confidence": result["agreement_ratio"],
                "reject_message": "죄송합니다. 저는 반도체 패키징 전문가라 그 질문에는 답할 수 없습니다."
            }

        # Case 2: 불확실하거나(Uncertain), 의도가 '복합 분석(Complex)'인 경우 -> LLM
        elif result["is_uncertain"] or result["final_label_id"] == 1:
            reason = "Uncertain" if result["is_uncertain"] else "Complex Intent"
            return {
                "should_use_llm": True,
                "reason": reason,
                "label": result["final_label"],
                "confidence": result["agreement_ratio"]
            }

        # Case 3: 확실하고 단순한 질문 -> LLM으로 처리 (기존 방식 유지)
        else:
            return {
                "should_use_llm": True,
                "reason": "Simple Query",
                "label": result["final_label"],
                "confidence": result["agreement_ratio"]
            }
