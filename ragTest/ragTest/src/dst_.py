"""
dst_manager.py
DST (Dialogue State Tracker)
- 첫 발화: intent 슬롯 전체 추론
- ACTIVE → DST 채움
- NONE → CLARIFICATION_QUESTIONS 질문
- 답변 오면 → 규칙 기반으로 해당 슬롯 채움
- system_setting: 6개 추론 후 가장 confidence 높은 그룹 확정
"""

import json
import torch
import sys
from pathlib import Path
from datetime import datetime
from transformers import AutoTokenizer
sys.path.append(str(Path(__file__).resolve().parents[1] / "experiment" / "slot_filling"))
from model import SlotFillingModel
from preprocess import SLOT_REGISTRY, get_slot_type, get_slot_description, get_candidates

# ── 설정 ──────────────────────────────────────────────────────────────────────
CFG = {
    "model_name":     "klue/roberta-base",
    "checkpoint_dir": "checkpoints/slot_filling", # "checkpoints_finetune", # 
    "max_length":     128,
}

# ── 인텐트별 슬롯 목록 ────────────────────────────────────────────────────────
INTENT_SLOTS = {
    "set_threshold":              ["window_name", "threshold_type", "threshold_value"],
    "set_size":                   ["window_name", "size_type", "size_value"],
    "set_option":                 ["window_name", "option_type", "option_value"],
    "system_setting":             ["settingNumPropertyName", "settingNumValue",
                                   "settingBoolPropertyName", "settingBoolValue",
                                   "settingColorPropertyName", "setColorValue"],
    "set_parameter":              ["window_name", "parameter_name", "parameter_value"],
    "geometry_set":               ["window_name", "geometry_position", "coordinate_value"],
    "roi_collection_control":     ["window_name", "roi_type", "roi_action"],
    "calibration_control":        ["action_type", "button_action", "shape_type",
                                   "similarity_value", "reference_type",
                                   "reticle_type", "camera_type"],
    "history_control":            ["filter_type", "date_range", "camera_type",
                                   "history_inspection_type", "button_action"],
    "open_window":                ["window_name"],
    "change_operation":           ["operation"],
    "inspection_execute":         ["window_name", "inspection_type"],
    "auto_configuration_execute": ["window_name", "auto_type"],
    "recipe_management":          ["action", "recipe_name", "target_name"],
    "ui_navigation_execute":      ["window_name", "tab_name"],
}

# ── system_setting 그룹 ───────────────────────────────────────────────────────
SYSTEM_SETTING_GROUPS = {
    "num":   ["settingNumPropertyName",   "settingNumValue"],
    "bool":  ["settingBoolPropertyName",  "settingBoolValue"],
    "color": ["settingColorPropertyName", "setColorValue"],
}
# 그룹별 PropertyName 슬롯 (confidence 기준)
SYSTEM_SETTING_PROPERTY_SLOT = {
    "num":   "settingNumPropertyName",
    "bool":  "settingBoolPropertyName",
    "color": "settingColorPropertyName",
}

# ── calibration action_type → 필요 슬롯 ──────────────────────────────────────
CALIBRATION_REQUIRED = {
    "button":           ["action_type", "button_action"],
    "shape_similarity": ["action_type", "shape_type", "similarity_value"],
    "reference_select": ["action_type", "reference_type"],
    "reticle_type":     ["action_type", "reticle_type"],
    "camera":           ["action_type", "camera_type"],
}

# ── history filter_type → 필요 슬롯 ──────────────────────────────────────────
HISTORY_REQUIRED = {
    "date":       ["filter_type", "date_range"],
    "camera":     ["filter_type", "camera_type"],
    "inspection": ["filter_type", "history_inspection_type"],
    "button":     ["filter_type", "button_action"],
}

# ── 고정 질문 ─────────────────────────────────────────────────────────────────
CLARIFICATION_QUESTIONS = {
    "window_name":              "어떤 창에서 설정하시겠습니까? (lga / bga / qfn / mapping / strip / calibration)",
    "threshold_type":           "어떤 임계값을 설정하시겠습니까? (예: ScratchThreshold, BallThreshold)",
    "threshold_value":          "임계값을 입력해주세요. (예: 50-100, 200)",
    "size_type":                "어떤 크기를 설정하시겠습니까? (예: ScratchSize, ForeignMaterialSize)",
    "size_value":               "크기 값을 입력해주세요. (예: 100-200)",
    "option_type":              "어떤 옵션을 변경하시겠습니까? (EdgeDetectMode / EdgeDetectDirection / FirstPinType / RotateAngle)",
    "option_value":             "옵션 값을 선택해주세요.",
    "settingNumPropertyName":   "설정할 수치 속성 이름을 입력해주세요. (예: LgaPadPitch, BgaBallSizeDiameter)",
    "settingNumValue":          "수치 값을 입력해주세요.",
    "settingBoolPropertyName":  "설정할 기능 이름을 입력해주세요. (예: UseLgaFirstPin, IsMappingUsed)",
    "settingBoolValue":         "활성화 여부를 입력해주세요. (true / false)",
    "settingColorPropertyName": "설정할 색상 속성 이름을 입력해주세요. (예: BgaMissingBallColor)",
    "setColorValue":            "색상을 입력해주세요. (예: Red, Blue, White)",
    "parameter_name":           "설정할 파라미터를 선택해주세요. (OutlineWidth / PackageThresholdDiff)",
    "parameter_value":          "파라미터 값을 입력해주세요.",
    "geometry_position":        "ROI 위치를 선택해주세요. (예: PackageRoiTop_, FirstPinRoi_)",
    "coordinate_value":         "ROI 좌표를 입력해주세요. (예: 10-20-30-40)",
    "roi_type":                 "어떤 ROI를 대상으로 하시겠습니까? (예: PadRois, DontCareRoi, SurfaceRoi)",
    "roi_action":               "ROI 동작을 선택해주세요. (add / delete / reset)",
    "action_type":              "보정 동작을 선택해주세요. (button / shape_similarity / reference_select / reticle_type / camera)",
    "button_action":            "실행할 버튼을 선택해주세요. (Test / LightSave)",
    "shape_type":               "도형 유형을 선택해주세요. (rectangle / circle)",
    "similarity_value":         "유사도 값을 입력해주세요. (0~100)",
    "reference_type":           "기준 선택 방식을 선택해주세요. (MULTIOBJECT / CENTER / BIGGEST)",
    "reticle_type":             "십자선 타입을 선택해주세요. (NONE / DEFAULT / FULLSIZE)",
    "camera_type":              "카메라를 선택해주세요. (Mapping / SettingX1 / SettingX2 / PRS / BarCode)",
    "filter_type":              "기록 필터 종류를 선택해주세요. (date / camera / inspection / button)",
    "date_range":               "조회할 날짜 범위를 입력해주세요. (예: 2024-01-01_2024-01-31)",
    "history_inspection_type":  "검사 종류를 선택해주세요. (Mapping / Mark / Qfn / Bga / Lga)",
    "inspection_type":          "실행할 검사 종류를 선택해주세요.",
    "auto_type":                "자동 설정 유형을 선택해주세요. (AutoRoiGenerate / AutoThresholdSet)",
    "action":                   "레시피 동작을 선택해주세요. (add / copy / rename / delete / select)",
    "recipe_name":              "대상 레시피 이름을 입력해주세요.",
    "target_name":              "새 레시피 이름을 입력해주세요.",
    "operation":                "장비 모드를 선택해주세요. (RUN / SETUP / PRS_RETEACH / MAPPING_RETEACH)",
    "tab_name":                 "이동할 탭을 선택해주세요. (예: Package / Surface / Sawing / Result)",
    "__system_setting_group__": "어떤 설정을 변경하시겠습니까? (수치 / 활성화여부 / 색상)"
}


# ── 모델 로드 ─────────────────────────────────────────────────────────────────
def load_model(cfg: dict):
    with open(f"{cfg['checkpoint_dir']}/candidate_vocab.json", encoding="utf-8") as f:
        candidate_vocab = json.load(f)
    tokenizer = AutoTokenizer.from_pretrained(cfg["model_name"])
    model = SlotFillingModel(
        model_name=cfg["model_name"],
        num_candidate_values=len(candidate_vocab),
    )
    model.load_state_dict(
        torch.load(f"{cfg['checkpoint_dir']}/best_model.pt", map_location="cpu", weights_only=False)
    )
    model.eval()
    return model, tokenizer, candidate_vocab


# ── 슬롯 1개 추론 (status + value + confidence) ───────────────────────────────
def infer_single_slot(utterance, slot_name, model, tokenizer, candidate_vocab, max_length=128):
    slot_desc = get_slot_description(slot_name)
    slot_type = get_slot_type(slot_name, "")
    candidates = get_candidates(slot_name, "")

    enc = tokenizer(
        utterance, slot_desc,
        max_length=max_length, truncation=True, padding="max_length",
        return_offsets_mapping=True, return_tensors="pt",
    )
    input_ids      = enc["input_ids"]
    attention_mask = enc["attention_mask"]
    token_type_ids = enc.get("token_type_ids", torch.zeros_like(input_ids))

    with torch.no_grad():
        s_logits, c_logits, ss_logits, se_logits = model(
            input_ids, attention_mask, token_type_ids
        )

    # status + confidence
    status_probs = torch.softmax(s_logits, dim=-1)[0]
    active_conf  = status_probs[1].item()
    status = "ACTIVE" if s_logits.argmax(dim=-1).item() == 1 else "NONE"

    value = ""
    if status == "ACTIVE":
        if slot_type == "categorical" and candidates:
            cand_indices = [candidate_vocab.get(c, 1) for c in candidates]
            best = c_logits[0, cand_indices].argmax().item()
            value = candidates[best]
        elif slot_type == "span":
            pred_s = ss_logits.argmax(dim=-1).item()
            pred_e = se_logits.argmax(dim=-1).item()
            if pred_e < pred_s:
                pred_e = pred_s

            ids = input_ids[0][pred_s:pred_e + 1].tolist()
            raw = tokenizer.decode(ids, skip_special_tokens=True).strip()

            # 🔹 공백 제거 (span 후처리)
            value = raw.replace(" ", "")
        

    return {"status": status, "value": value, "confidence": active_conf}


# ── system_setting 그룹 판별 ──────────────────────────────────────────────────
def resolve_system_setting_group(utterance, model, tokenizer, candidate_vocab, max_length=128):
    """
    6개 슬롯 전부 추론 → PropertyName confidence 기준으로 그룹 확정
    반환: (group_name, slot_results)
      group_name: "num" / "bool" / "color"
      slot_results: {slot_name: {"status", "value", "confidence"}}
    """
    all_slots = (SYSTEM_SETTING_GROUPS["num"] +
                 SYSTEM_SETTING_GROUPS["bool"] +
                 SYSTEM_SETTING_GROUPS["color"])

    slot_results = {}
    for slot_name in all_slots:
        slot_results[slot_name] = infer_single_slot(
            utterance, slot_name, model, tokenizer, candidate_vocab, max_length
        )

    # PropertyName ACTIVE → 해당 그룹 확정 (confidence 가장 높은 걸로)
    # group_confidences = {}
    # for group, prop_slot in SYSTEM_SETTING_PROPERTY_SLOT.items():
    #     group_confidences[group] = slot_results[prop_slot]["confidence"]

    # best_group = max(group_confidences, key=lambda g: group_confidences[g])
    group_scores = {} # 속성이름, 밸류 점수 합쳐서 높은 걸로

    for group, slots in SYSTEM_SETTING_GROUPS.items():
        score = 0.0
        for slot in slots:
            score += slot_results[slot]["confidence"]
        group_scores[group] = score

    best_group = max(group_scores, key=lambda g: group_scores[g])

    if group_scores[best_group] < 0.8:
        return None, slot_results

    return best_group, slot_results




# ── DST State ─────────────────────────────────────────────────────────────────
class DSTState:
    def __init__(self, turn_id: str, utterance: str, intent: str):
        self.turn_id  = turn_id
        self.utterance = utterance
        self.intent   = intent
        self.slots    = {}      # {slot_name: value}
        self.pending  = []      # 아직 못 채운 슬롯 목록
        self.complete = False
        # system_setting 확정 그룹
        self.system_setting_group = None  # "num" / "bool" / "color"
        self.retry_count = {}

    def to_dict(self):
        return {
            "turn_id":  self.turn_id,
            "utterance": self.utterance,
            "intent":   self.intent,
            "slots":    self.slots,
            "pending":  self.pending,
            "complete": self.complete,
        }


# ── DST Manager ───────────────────────────────────────────────────────────────
class DSTManager:
    def __init__(self, model, tokenizer, candidate_vocab, cfg=CFG):
        self.model           = model
        self.tokenizer       = tokenizer
        self.candidate_vocab = candidate_vocab
        self.max_length      = cfg["max_length"]
        self.state: DSTState = None

    # ── 첫 발화 처리 ──────────────────────────────────────────────────────────
    def process_first_utterance(self, utterance: str, intent: str):
        turn_id    = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.state = DSTState(turn_id, utterance, intent)

        if intent == "system_setting":
            self._process_system_setting(utterance)
        elif intent == "calibration_control":
            self._process_calibration(utterance)
        elif intent == "history_control":
            self._process_history(utterance)
        else:
            self._process_general_intent(utterance, intent)

        return self.state, self._next_question()

    # ── 후속 답변 처리 ────────────────────────────────────────────────────────
    def process_answer(self, answer: str) -> tuple[DSTState, str | None]:
        """
        pending 슬롯에 대한 사용자 답변 처리
        → 모델 추론으로 슬롯 값 추출 (범주형: candidates에서 선택, 스팬: 텍스트 추출)
        → 모델이 NONE 뱉거나 매칭 실패 시 답변 텍스트 그대로 fallback
        반환: (state, 다음 질문 or None)
        """
        CONF_THRESHOLD = 0.8
    
        if not self.state or not self.state.pending:
            return self.state, None

        slot_name = self.state.pending[0]

        # ── system_setting 그룹 질문 처리 ──────────────────────────────────
        if slot_name == "__system_setting_group__":
            group_map = {
                "수치": "num", "숫자": "num", "num": "num", "number": "num",
                "활성화": "bool", "bool": "bool", "boolean": "bool", "여부": "bool",
                "색상": "color", "color": "color", "컬러": "color",
            }
            group = group_map.get(answer.strip().lower())
            if group:
                self.state.system_setting_group = group
                self.state.pending.pop(0)
                for s in SYSTEM_SETTING_GROUPS[group]:
                    self.state.pending.append(s)
                question = self._next_question()
                if not question:
                    self.state.complete = True
                return self.state, question
            else:
                return self.state, CLARIFICATION_QUESTIONS["__system_setting_group__"]

        slot_type = get_slot_type(slot_name, "")
        candidates = get_candidates(slot_name, "")

        # ── 모델 추론 ──────────────────────────────────────────────────────
        result = infer_single_slot(
            answer, slot_name, self.model, self.tokenizer,
            self.candidate_vocab, self.max_length
        )

        if (
                result["status"] == "ACTIVE"
                and result["value"]
                and result["confidence"] >= CONF_THRESHOLD
            ):
                value = result["value"]
        else:
            # 범주형 직접 매칭 시도
            matched = None
            if slot_type == "categorical" and candidates:
                matched = next(
                    (c for c in candidates if c.lower() == answer.strip().lower()), None
                )

            if matched:
                value = matched
            else:
                # retry 카운터 확인
                retry = self.state.retry_count.get(slot_name, 0)
                if retry < 1:
                    # 한 번 더 질문
                    self.state.retry_count[slot_name] = retry + 1
                    question = CLARIFICATION_QUESTIONS.get(slot_name, f"{slot_name} 값을 입력해주세요.")
                    return self.state, f"다시 입력해주세요. {question}"
                else:
                    # 2번 실패 → 종료
                    self.state.complete = True
                    self.state.pending = []
                    print("매치 실패. 종료")
                    return self.state, None

        self.state.slots[slot_name] = value
        self.state.pending.pop(0)

        # system_setting: PropertyName 채워졌으면 그룹 고정
        if slot_name in SYSTEM_SETTING_PROPERTY_SLOT.values():
            for group, prop in SYSTEM_SETTING_PROPERTY_SLOT.items():
                if prop == slot_name:
                    self.state.system_setting_group = group
                    self._filter_system_setting_pending() 
                    break

        # calibration: action_type 채워졌으면 불필요 pending 정리
        if slot_name == "action_type":
            self._set_calibration_pending(value)

        # history: filter_type 채워졌으면 불필요 pending 정리
        if slot_name == "filter_type":
            self._set_history_pending(value)

        question = self._next_question()
        if not question:
            self.state.complete = True

        return self.state, question

    # ── calibration 그룹 판별 ──────────────────────────────────────────────────
    def _process_calibration(self, utterance: str):
        CONF_THRESHOLD = 0.8
        r = infer_single_slot(
            utterance, "action_type", self.model, self.tokenizer,
            self.candidate_vocab, self.max_length
        )
        if r["status"] == "ACTIVE" and r["value"]:
            action = r["value"]
            self.state.slots["action_type"] = action
            for slot_name in CALIBRATION_REQUIRED.get(action, []):
                sr = infer_single_slot(
                    utterance, slot_name, self.model, self.tokenizer,
                    self.candidate_vocab, self.max_length
                )
                if (
                    sr["status"] == "ACTIVE"
                    and sr["value"]
                    and sr["confidence"] >= CONF_THRESHOLD
                ):
                    self.state.slots[slot_name] = sr["value"]
                else:
                    self.state.pending.append(slot_name)
        else:
            if (
                r["status"] == "ACTIVE"
                and r["value"]
                and r["confidence"] >= CONF_THRESHOLD
            ):
                action = r["value"]
            self.state.pending.append("action_type")

        if not self.state.pending:
            self.state.complete = True

    # ── history 그룹 판별 ──────────────────────────────────────────────────
    def _process_history(self, utterance: str):
        CONF_THRESHOLD = 0.8
        r = infer_single_slot(
            utterance, "filter_type", self.model, self.tokenizer,
            self.candidate_vocab, self.max_length
        )
        if r["status"] == "ACTIVE" and r["value"]:
            ftype = r["value"]
            self.state.slots["filter_type"] = ftype
            for slot_name in HISTORY_REQUIRED.get(ftype, []):
                sr = infer_single_slot(
                    utterance, slot_name, self.model, self.tokenizer,
                    self.candidate_vocab, self.max_length
                )
                if (
                    sr["status"] == "ACTIVE"
                    and sr["value"]
                    and sr["confidence"] >= CONF_THRESHOLD
                ):
                    self.state.slots[slot_name] = sr["value"]
                else:
                    self.state.pending.append(slot_name)
                
        else:
            self.state.pending.append("filter_type")

        if not self.state.pending:
            self.state.complete = True
    # ── 내부: 일반 인텐트 처리 ────────────────────────────────────────────────
    def _process_general_intent(self, utterance: str, intent: str):
        slot_names = INTENT_SLOTS.get(intent, [])
        for slot_name in slot_names:
            result = infer_single_slot(
                utterance, slot_name, self.model, self.tokenizer,
                self.candidate_vocab, self.max_length
            )
            if result["status"] == "ACTIVE" and result["value"]:
                self.state.slots[slot_name] = result["value"]
            else:
                self.state.pending.append(slot_name)

        # calibration: action_type ACTIVE면 불필요 슬롯 pending 정리
        if intent == "calibration_control" and "action_type" in self.state.slots:
            self._filter_calibration_pending(self.state.slots["action_type"])

        # history: filter_type ACTIVE면 불필요 슬롯 pending 정리
        if intent == "history_control" and "filter_type" in self.state.slots:
            self._set_calibration_pending(self.state.slots["filter_type"])

        if not self.state.pending:
            self.state.complete = True

    # ── 내부: system_setting 처리 ─────────────────────────────────────────────
    def _process_system_setting(self, utterance: str):
        group, slot_results = resolve_system_setting_group(
            utterance, self.model, self.tokenizer, self.candidate_vocab, self.max_length
        )
        
        all_none = all(
            slot_results[prop]["status"] == "NONE"
            for prop in SYSTEM_SETTING_PROPERTY_SLOT.values()
        )
        if all_none:
        # 그룹 질문을 pending에 넣음
            self.state.pending.append("__system_setting_group__")
        else:
            self.state.system_setting_group = group
            active_slots = SYSTEM_SETTING_GROUPS[group]
            for slot_name in active_slots:
                result = slot_results[slot_name]
                if result["status"] == "ACTIVE" and result["value"]:
                    self.state.slots[slot_name] = result["value"]
                else:
                    self.state.pending.append(slot_name)

            if not self.state.pending:
                self.state.complete = True

    # ── 내부: calibration pending 정리 ───────────────────────────────────────
    def _filter_calibration_pending(self, action_type_value: str):
        required = CALIBRATION_REQUIRED.get(action_type_value, [])
        # required에 없는 슬롯은 pending에서 제거
        self.state.pending = [
            s for s in self.state.pending if s in required
        ]

    def _set_calibration_pending(self, action_type_value: str):
        for slot_name in CALIBRATION_REQUIRED.get(action_type_value, []):
            if slot_name not in self.state.slots and slot_name not in self.state.pending:
                self.state.pending.append(slot_name)

    # ── 내부: history pending 정리 ────────────────────────────────────────────
    def _filter_history_pending(self, filter_type_value: str):
        required = HISTORY_REQUIRED.get(filter_type_value, [])
        self.state.pending = [
            s for s in self.state.pending if s in required
        ]
    def _set_history_pending(self, filter_type_value: str):
        for slot_name in HISTORY_REQUIRED.get(filter_type_value, []):
            if slot_name not in self.state.slots and slot_name not in self.state.pending:
                self.state.pending.append(slot_name)

    # ── 내부: system_setting 그룹 확정 후 pending 정리 ───────────────────────
    def _filter_system_setting_pending(self):
        group = self.state.system_setting_group
        if not group:
            return
        keep = SYSTEM_SETTING_GROUPS[group]
        self.state.pending = [s for s in self.state.pending if s in keep]

    # ── 내부: 다음 질문 반환 ──────────────────────────────────────────────────
    def _next_question(self) -> str | None:
        if not self.state.pending:
            self.state.complete = True
            return None
        slot_name = self.state.pending[0]
        return CLARIFICATION_QUESTIONS.get(slot_name, f"{slot_name} 값을 입력해주세요.")


# ── 테스트용 CLI ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    model, tokenizer, candidate_vocab = load_model(CFG)
    manager = DSTManager(model, tokenizer, candidate_vocab)

    print("=== DST 테스트 ===")
    print("형식: <인텐트> <발화>  (예: set_threshold 임계값 올려줘)")
    print("후속 답변은 그냥 입력")
    print("종료: exit\n")

    waiting_answer = False

    while True:
        user_input = input("입력 > ").strip()
        if user_input.lower() == "exit":
            break

        if not waiting_answer:
            parts = user_input.split(" ", 1)
            if len(parts) < 2:
                print("형식: <인텐트> <발화>")
                continue
            intent, utterance = parts
            state, question = manager.process_first_utterance(utterance, intent)
        else:
            state, question = manager.process_answer(user_input)

        print(f"\nDST: {json.dumps(state.to_dict(), ensure_ascii=False, indent=2)}")

        if question:
            print(f"\n질문: {question}")
            waiting_answer = True
        else:
            print("\n✅ 슬롯 필링 완료!")
            waiting_answer = False
