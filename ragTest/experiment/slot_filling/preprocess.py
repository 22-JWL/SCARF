"""
preprocess.py
원본 JSONL → 슬롯 단위 flatten → train/val/test stratified split
"""

import json
import random
from pathlib import Path
from collections import defaultdict

# ── SLOT REGISTRY ─────────────────────────────────────────────────────────────
SLOT_REGISTRY = {

    # ── 공통 ──────────────────────────────────────────────────────────────────
    "window_name": {
        "type": "categorical",
        "description": "사용자가 대상으로 하는 창 이름입니다. (lga, bga, qfn, mapping, strip 등)",
        "candidates": ["lga", "qfn", "bga", "mapping", "strip",
                       "history", "light", "calibration", "setting", "lot"],
    },

    # ── set_threshold ──────────────────────────────────────────────────────────
    "threshold_type": {
        "type": "categorical",
        "description": "설정할 임계값 종류입니다. (PackageThreshold, BallThreshold 등)",
        "candidates": [
            "PackageThreshold", "FirstPinThreshold", "MultiPadThreshold",
            "LeadThreshold", "ScratchThreshold", "ForeignMaterialThreshold",
            "ContaminationThreshold", "OutlineThreshold", "RejectMarkThreshold",
            "PadThreshold", "PatternThreshold", "BallThreshold", "MarkThreshold",
        ],
    },
    "threshold_value": {
        "type": "span",
        "description": "설정할 임계값 수치입니다. (예: 100, 50-200, 100,200)",
    },

    # ── set_size ───────────────────────────────────────────────────────────────
    "size_type": {
        "type": "categorical",
        "description": "설정할 크기 종류입니다. (ScratchSize, ForeignMaterialSize 등)",
        "candidates": [
            "PadContaminationSize", "LeadContaminationSize", "ScratchSize",
            "ForeignMaterialSize", "ContaminationSize", "RejectMarkSize",
        ],
    },
    "size_value": {
        "type": "span",
        "description": "설정할 크기 수치입니다.",
    },

    # ── set_option ─────────────────────────────────────────────────────────────
    "option_type": {
        "type": "categorical",
        "description": "설정할 옵션 종류입니다. (EdgeDetectMode, FirstPinType 등)",
        "candidates": ["EdgeDetectDirection", "EdgeDetectMode", "FirstPinType", "RotateAngle"],
    },
    "option_value": {
        "type": "categorical",
        "description": "선택할 옵션 값입니다. EdgeDetectDirection: 내부에서외부(InToOut), 외부에서내부(OutToIn). EdgeDetectMode: 흑백(BlackToWhite), 백흑(WhiteToBlack). FirstPinType: SmallPad, Notch, Chamfer. RotateAngle: 0, 90, 180, 270.",
        "candidates": ["BlackToWhite", "WhiteToBlack", "InToOut", "OutToIn",
                       "SmallPad", "Notch", "Chamfer", "0", "90", "180", "270"],
    },

    # ── geometry_set ───────────────────────────────────────────────────────────
    "geometry_position": {
        "type": "categorical",
        "description": "ROI를 설정할 위치입니다. (PackageRoiTop_, FirstPinRoi_ 등)",
        "candidates": [
            "PackageRoiTop_", "PackageRoiLeft_", "PackageRoiBottom_", "PackageRoiRight_",
            "PackageModelRoi_", "FirstPinRoi_", "RejectMarkRoi_", "PadRoi_",
            "GridRoi_", "CodeRoi_", "StripRois",
        ],
    },
    "coordinate_value": {
        "type": "span",
        "description": "ROI 좌표 값입니다. (예: 10-20-30-40)",
    },

    # ── set_number (system_setting 수치) ───────────────────────────────────────
    "settingNumPropertyName": {
        "type": "categorical",
        "description": "숫자(Number) 타입 설정 속성 이름입니다.",
        "candidates": [
            # lga
            "LgaPackageSizeWidth", "LgaPackageSizeHeight", "LgaCornerDegree",
            "LgaPadSizeWidth", "LgaPadSizeHeight", "LgaPadArea", "LgaPadPitch",
            "LgaPadOffsetX", "LgaPadOffsetY", "LgaPadOffsetT", "LgaPadPerimeter",
            "LgaLeadSizeWidth", "LgaLeadSizeHeight", "LgaLeadArea", "LgaLeadPitch",
            "LgaLeadOffsetX", "LgaLeadOffsetY", "LgaLeadOffsetT", "LgaLeadPerimeter",
            # bga
            "BgaPackageSizeWidth", "BgaPackageSizeHeight", "BgaCornerDegree",
            "BgaSawOffsetX", "BgaSawOffsetY", "BgaSawOffsetXStandard", "BgaSawOffsetYStandard",
            "BgaBallSizeDiameter", "BgaBallSizeDiameterStandard", "BgaBallPitch", "BgaBallPitchStandard",
            # qfn
            "QfnPackageSizeWidth", "QfnPackageSizeHeight", "QfnCornerDegree",
            "QfnSawOffsetY", "QfnSawOffsetX",
            "QfnPadSizeWidth", "QfnPadSizeHeight", "QfnPadArea",
            "QfnLeadSizeWidth", "QfnLeadSizeHeight", "QfnLeadArea", "QfnLeadPitch",
            "QfnLeadOffsetX", "QfnLeadOffsetY", "QfnLeadOffsetT", "QfnLeadPerimeter",
            # mapping
            "MapPackageSizeWidth", "MapPackageSizeHeight",
            "MappingSawOffsetY", "MappingSawOffsetX",
            "MarkCount", "MapTextOffsetX", "MapTextOffsetY", "MapTextOffsetT",
            "MapCornerDegree",
            # recipe
            "TrayRowCount", "TrayColCount", "FovRowCount", "FovColCount",
            "BlockRowCount", "BlockColCount", "PackageHeight", "PackageWidth",
            # etc
            "SaveOption", "SaveDays", "DBSaveDays", "InpectionModeSelectedItem",
        ],
    },
    "settingNumValue": {
        "type": "span",
        "description": "설정할 수치 값입니다.",
    },

    # ── set_boolean (system_setting 불리언) ────────────────────────────────────
    "settingBoolPropertyName": {
        "type": "categorical",
        "description": "ON/OFF, true/false, 활성화/비활성화(Boolean) 타입 설정 속성 이름입니다. (UseLgaFirstPin, UseBgaBallCount 등)",
        "candidates": [
            # lga
            "UseLgaNoDevice", "UseLgaPackageSize", "UseLgaPackageOffset", "UseLgaCornerDegree",
            "UseLgaFirstPin", "UseLgaPadCount", "UseLgaPadSize", "UseLgaPadPitch",
            "UseLgaPadOffset", "UseLgaPadArea", "UseLgaPadContamination", "UseLgaPadPerimeter",
            "UseLgaLeadCount", "UseLgaLeadSize", "UseLgaLeadPitch", "UseLgaLeadOffset",
            "UseLgaLeadArea", "UseLgaLeadContamination", "UseLgaLeadPerimeter",
            "UseLgaScratch", "UseLgaForeignMaterial", "UseLgaContamination",
            "UseLgaSawOffset", "UseLgaChipping", "UseLgaBurr", "UseLgaRejectMark",
            # bga
            "UseBgaNoDevice", "UseBgaPackageSize", "UseBgaPackageOffset", "UseBgaCornerDegree",
            "UseBgaFirstPin", "UseBgaPattern", "UseBgaBallCount", "UseBgaBallSize",
            "UseBgaBallPitch", "UseBgaBallBridging", "UseBgaExtraBall", "UseBgaMissingBall",
            "UseBgaCrackBall", "UseBgaScratch", "UseBgaForeignMaterial", "UseBgaContamination",
            "UseBallPosition", "UseBgaSawOffset", "UseBgaChipping", "UseBgaBurr", "UseBgaRejectMark",
            # qfn
            "UseQfnNoDevice", "UseQfnPackageSize", "UseQfnPackageOffset", "UseQfnCornerDegree",
            "UseQfnFirstPin", "UseQfnPadSize", "UseQfnPadArea",
            "UseQfnLeadCount", "UseQfnLeadSize", "UseQfnLeadPitch", "UseQfnLeadOffset",
            "UseQfnLeadArea", "UseQfnLeadContamination", "UseQfnLeadPerimeter",
            "UseQfnScratch", "UseQfnForeignMaterial", "UseQfnContamination",
            "UseQfnSawOffset", "UseQfnChipping", "UseQfnBurr", "UseQfnRejectMark",
            # mapping
            "UseMapNoDevice", "UseMapPackageSize", "UseMapPackageOffset", "UseMapCornerDegree",
            "UseMapNoMark", "UseMapMarkCount", "UseMapWrongMark", "UseMapTextAngle",
            "UseMapTextOffset", "UseMapDataCode", "UseMapMissingChar",
            "UseMapScratch", "UseMapForeignMaterial", "UseMapContamination",
            "UseMapSawOffset", "UseMapChipping", "UseMapBurr", "UseMapRejectMark",
            # recipe
            "IsMappingUsed", "IsPrsUsed", "IsBarcodeUsed",
        ],
    },
    "settingBoolValue": {
        "type": "categorical",
        "description": "기능 활성화 여부입니다. (true / false)",
        "candidates": ["true", "false"],
    },
    # setBoolValue = settingBoolValue 별칭 (데이터에서 혼용)
    "setBoolValue": {
        "type": "categorical",
        "description": "기능 활성화 여부입니다. (true / false)",
        "candidates": ["true", "false"],
    },
    "history_inspection_type": {
        "type": "categorical",
        "description": "기록 창 검사 종류 필터입니다. (NotSelected, Mapping, Mark 등)",
        "candidates": [
            "NotSelected", "Mapping", "Mark", "Qfn",
            "Bga", "Lga", "DataCode", "BottomDataCode", "Strip"
        ],
    },

    # ── set_color (system_setting 색상) ────────────────────────────────────────
    "settingColorPropertyName": {
        "type": "categorical",
        "description": "색상(Color) 타입 설정 속성 이름입니다. (BgaNoDeviceColor, LgaScratchColor 등)",
        "candidates": [
            # bga
            "BgaNoDeviceColor", "BgaPackageSizeColor", "BgaPackageOffsetColor", "BgaCornerDegreeColor",
            "BgaFirstPinColor", "BgaPatternColor", "BgaBallCountColor", "BgaBallSizeColor",
            "BgaBallPitchColor", "BgaBallBridgingColor", "BgaExtraBallColor", "BgaMissingBallColor",
            "BgaCrackBallColor", "BgaScratchColor", "BgaForeignMaterialColor", "BgaContaminationColor",
            "BgaBallPositionColor", "BgaSawOffsetColor", "BgaChippingColor", "BgaBurrColor",
            "BgaRejectMarkColor", "BgaXOutColor", "BgaXOut2Color",
            # lga
            "LgaNoDeviceColor", "LgaPackageSizeColor", "LgaPackageOffsetColor", "LgaCornerDegreeColor",
            "LgaFirstPinColor", "LgaPadCountColor", "LgaPadSizeColor", "LgaPadPitchColor",
            "LgaPadOffsetColor", "LgaPadAreaColor", "LgaPadContaminationColor", "LgaPadPerimeterColor",
            "LgaLeadCountColor", "LgaLeadSizeColor", "LgaLeadPitchColor", "LgaLeadOffsetColor",
            "LgaLeadAreaColor", "LgaLeadContaminationColor", "LgaLeadPerimeterColor",
            "LgaScratchColor", "LgaForeignMaterialColor", "LgaContaminationColor",
            "LgaSawOffsetColor", "LgaChippingColor", "LgaBurrColor", "LgaRejectMarkColor",
            # qfn
            "QfnNoDeviceColor", "QfnPackageSizeColor", "QfnPackageOffsetColor", "QfnCornerDegreeColor",
            "QfnFirstPinColor", "QfnPadSizeColor", "QfnPadAreaColor", "QfnLeadCountColor",
            "QfnLeadSizeColor", "QfnLeadPitchColor", "QfnLeadOffsetColor", "QfnLeadAreaColor",
            "QfnLeadContaminationColor", "QfnLeadPerimeterColor", "QfnScratchColor",
            "QfnForeignMaterialColor", "QfnContaminationColor", "QfnSawOffsetColor",
            "QfnChippingColor", "QfnBurrColor", "QfnRejectMarkColor", "QfnXOutColor",
            # mapping
            "MapNoDeviceColor", "MapPackageSizeColor", "MapPackageOffsetColor", "MapCornerDegreeColor",
            "MapNoMarkColor", "MapMarkCountColor", "MapWrongMarkColor", "MapTextAngleColor",
            "MapTextOffsetColor", "MapDataCodeColor", "MapMissingCharColor", "MapScratchColor",
            "MapForeignMaterialColor", "MapContaminationColor", "MappingSawOffsetColor",
            "MapChippingColor", "MapBurrColor", "MapRejectMarkColor", "MapXOutColor", "MapXOut2Color",
        ],
    },
    "setColorValue": {
        "type": "categorical",
        "description": "설정할 색상 값입니다. (Red, Green, Blue 등)",
        "candidates": [
            "Red", "Green", "Blue", "Yellow", "Cyan", "Magenta",
            "Orange", "Purple", "Black", "White", "Gray", "Brown",
            "Pink", "Teal", "Navy", "Lime", "Olive", "Maroon", "Aqua", "Silver",
        ],
    },

    # ── roi_collection_control ─────────────────────────────────────────────────
    "roi_type": {
        "type": "categorical",
        "description": "제어할 ROI 종류입니다. (PadRois, BallRoi 등)",
        "candidates": [
            "PadRois", "SurfaceRoi", "DontCareRoi", "LeadRois",
            "PatternRois", "BallRoi", "SurfaceRois", "RejectMarkRoi",
            "MarkRoi"
        ],
    },
    "roi_action": {
        "type": "categorical",
        "description": "ROI에 대해 수행할 동작입니다. (add, delete, reset, read)",
        "candidates": ["add", "delete", "reset", "read"],
    },

    # ── inspection_execute ─────────────────────────────────────────────────────
    "inspection_type": {
        "type": "categorical",
        "description": "실행할 검사 종류입니다. (findBallsTeaching, inspectTeaching 등)",
        "candidates": [
            "findpadsTeaching", "findLeadsTeaching",
            "findSurfaceTeaching", "findSawingTeaching", "inspectRejectMarkTeaching",
            "inspectTeaching", "inspectPackageTeaching", "inspectPadAndLeadsTeaching",
            "inspectSurfaceTeaching", "inspectSawingTeaching",
            "findFirstPinAndPatternTeaching", "findBallsTeaching",
            "findPackagesTeaching", "inspectMarksAndDataCodeTeaching",
        ],
    },

    # ── auto_configuration_execute ─────────────────────────────────────────────
    "auto_type": {
        "type": "categorical",
        "description": "실행할 자동 설정 유형입니다. (AutoRoiGenerate, AutoThresholdSet 등)",
        "candidates": ["AutoRoiGenerate", "AutoThresholdSet", "findBallRoiAutoCommand"],
    },

    # ── calibration_control ────────────────────────────────────────────────────
    "action_type": {
        "type": "categorical",
        "description": "보정 창에서 수행할 동작 유형입니다. (button, shape_similarity 등)",
        "candidates": ["button", "shape_similarity", "reference_select", "reticle_type", "camera"],
    },
    "button_action": {
        "type": "categorical",
        "description": "실행할 버튼 동작입니다. (Test, LightSave, save, open)",
        "candidates": ["Test", "LightSave", "save", "open"],
    },
    "shape_type": {
        "type": "categorical",
        "description": "설정할 도형 유형입니다. (rectangle, circle)",
        "candidates": ["rectangle", "circle"],
    },
    "similarity_value": {
        "type": "span",
        "description": "도형 유사도 값입니다. (0~100)",
    },
    "reference_type": {
        "type": "categorical",
        "description": "기준 선택 방식입니다. (MULTIOBJECT, CENTER, BIGGEST)",
        "candidates": ["MULTIOBJECT", "CENTER", "BIGGEST"],
    },
    "reticle_type": {
        "type": "categorical",
        "description": "십자선 표시 타입입니다. (NONE, DEFAULT, FULLSIZE)",
        "candidates": ["NONE", "DEFAULT", "FULLSIZE"],
    },
    "camera_type": {
        "type": "categorical",
        "description": "카메라 유형입니다. (Mapping, SettingX1, PRS 등)",
        "candidates": ["Mapping", "SettingX1", "SettingX2", "PRS",
                       "BarCode", "TopBarCode", "Side", "NotSelected"],
    },

    # ── history_control ────────────────────────────────────────────────────────
    "filter_type": {
        "type": "categorical",
        "description": "기록 창 필터 유형입니다. (date, camera, inspection, button)",
        "candidates": ["date", "camera", "inspection", "button"],
    },
    "date_range": {
        "type": "span",
        "description": "조회할 날짜 범위입니다. (YYYY-MM-DD_YYYY-MM-DD 형식)",
    },

    # ── recipe_management ──────────────────────────────────────────────────────
    "action": {
        "type": "categorical",
        "description": "레시피에 대해 수행할 동작입니다. (add, copy, rename, delete, select)",
        "candidates": ["add", "copy", "rename", "delete", "select"],
    },
    "recipe_name": {
        "type": "span",
        "description": "대상 레시피 이름입니다.",
    },
    "target_name": {
        "type": "span",
        "description": "복사 또는 이름 변경 시 새로 생성될 레시피 이름입니다.",
    },

    # ── change_operation ───────────────────────────────────────────────────────
    "operation": {
        "type": "categorical",
        "description": "장비 모드 또는 재티칭 유형입니다. (RUN, SETUP, PRS_RETEACH, MAPPING_RETEACH)",
        "candidates": ["RUN", "SETUP", "PRS_RETEACH", "MAPPING_RETEACH"],
    },

    # ── ui_navigation ──────────────────────────────────────────────────────────
    "tab_name": {
        "type": "categorical",
        "description": "이동할 탭 이름입니다. (Package, Ball, Surface 등)",
        "candidates": [
            "Package", "Pads", "Leads", "Surface", "Sawing", "RejectMark",
            "DontCare", "Result", "FirstPinPattern", "Ball", "padLeads", "Mark",
            "PRS", "BarCode", "SettingX1", "SettingX2", "Mapping",
            "bottom", "setting", "pad", "tray", "vision",
        ],
    },

    # ── set_parameter ──────────────────────────────────────────────────────────
    "parameter_name": {
        "type": "categorical",
        "description": "설정할 파라미터 이름입니다. (OutlineWidth, PackageThresholdDiff)",
        "candidates": ["OutlineWidth", "PackageThresholdDiff"],
    },
    "parameter_value": {
        "type": "span",
        "description": "설정할 수치 값입니다.",
    },
}

# boolean intent에서는 value가 categorical
BOOLEAN_INTENTS = {"set_boolean"}

def _get_possible_slots(intent: str) -> list:
    """intent별 등장 가능한 슬롯 목록 (참고용)"""
    mapping = {
        "set_threshold":            ["window_name", "threshold_type", "threshold_value"],
        "set_size":                 ["window_name", "size_type", "size_value"],
        "set_option":               ["window_name", "option_type", "option_value"],
        # "set_number":               [ "settingNumPropertyName", "settingNumValue"],
        # "set_boolean":              [ "settingBoolPropertyName", "settingBoolValue"],
        # "set_color":                [ "settingColorPropertyName", "setColorValue"],
        "system_setting":           [ "settingNumPropertyName", "settingNumValue",
                                     "settingBoolPropertyName", "settingBoolValue",
                                     "settingColorPropertyName", "setColorValue"],
        "set_parameter":            ["window_name", "parameter_name", "parameter_value"],
        "geometry_set":             ["window_name", "geometry_position", "coordinate_value"],
        "roi_collection_control":   ["window_name", "roi_type", "roi_action"],
        "calibration_control":      ["action_type", "button_action", "shape_type",
                                     "similarity_value", "reference_type",
                                     "reticle_type", "camera_type"],
        "history_control":          ["filter_type", "date_range", "camera_type",
                                     "inspection_type", "button_action"],
        "open_window":              ["window_name"],
        "change_operation":         ["operation"],
        "inspection_execute":       ["window_name", "inspection_type"],
        "auto_configuration_execute": ["window_name", "auto_type"],
        "recipe_management":        ["action", "recipe_name", "target_name"],
        "ui_navigation_execute":    ["window_name", "tab_name"],
    }
    return mapping.get(intent, [])

def get_slot_type(slot_name: str, intent: str) -> str:
    info = SLOT_REGISTRY.get(slot_name)
    return info["type"] if info else "span"


def get_slot_description(slot_name: str) -> str:
    info = SLOT_REGISTRY.get(slot_name)
    return info["description"] if info else f"{slot_name} 슬롯입니다."


def get_candidates(slot_name: str, intent: str) -> list:
    info = SLOT_REGISTRY.get(slot_name, {})
    return info.get("candidates", [])


def find_char_offset(utterance: str, value: str):
    """발화에서 value의 char offset 탐색. 못 찾으면 (-1, -1)."""
    idx = utterance.find(value)
    if idx == -1:
        return -1, -1
    return idx, idx + len(value)


def flatten_sample(raw: dict) -> list:
    """
    발화 1개 → 슬롯별 샘플 리스트

    슬롯 값 형태 3가지를 모두 처리:
      형태 1: {"operation": "RUN"}                          # 값만 직접
      형태 2: {"size_value": {"value": "100", "start": 5}}  # dict, status 없음 → ACTIVE
      형태 3: {"action": {"value": "rename", "status": "ACTIVE"/"NONE"}}  # status 명시

    span 슬롯에서 start/end가 없으면 발화에서 value를 자동 탐색.
    """
    utterance = raw["utterance"]
    intent = raw["intent"]
    slots = raw.get("slots", {})

    samples = []

    for slot_name, slot_info in slots.items():
        slot_type = get_slot_type(slot_name, intent)

        # ── 형태 1: 값이 직접 문자열/숫자로 들어온 경우 ──────────────────
        if not isinstance(slot_info, dict):
            if slot_info is None:
                status, value, start, end = "NONE", "", -1, -1
            else:
                status = "ACTIVE"
                value = str(slot_info)
                start, end = -1, -1

        # ── 형태 2 & 3: dict인 경우 ──────────────────────────────────────
        else:
            raw_status = slot_info.get("status")    # "ACTIVE" / "NONE" / None
            raw_value  = slot_info.get("value")     # 실제값 / None / "null"

            # "null" 문자열도 None으로 통일
            if raw_value == "null":
                raw_value = None

            # status 명시된 경우 (형태 3)
            if raw_status is not None:
                if raw_value is None:
                    status = "NONE"
                else:
                    status = raw_status
            # status 없는 경우 (형태 2) → value 유무로 판단
            else:
                status = "ACTIVE" if raw_value is not None else "NONE"

            if status == "ACTIVE":
                value = str(raw_value)
                start = slot_info.get("start") if slot_info.get("start") is not None else -1
                end   = slot_info.get("end")   if slot_info.get("end")   is not None else -1
            else:
                value, start, end = "", -1, -1

        # ── span 슬롯에서 start/end 없으면 발화에서 자동 탐색 ────────────
        if slot_type == "span" and status == "ACTIVE" and value and start == -1:
            start, end = find_char_offset(utterance, value)

        samples.append({
            "utterance":        utterance,
            "intent":           intent,
            "slot_name":        slot_name,
            "slot_description": get_slot_description(slot_name),
            "slot_type":        slot_type,
            "candidates":       get_candidates(slot_name, intent),
            "status":           status,
            "value":            value,
            "span_start":       start,
            "span_end":         end,
        })

    return samples


# 다시 고친 버전. 테스트 안섞이게
def stratified_split_raw(raw_samples: list, ratios=(0.8, 0.1, 0.1)):
    """
    raw utterance 단위 stratified split
    """
    by_intent = defaultdict(list)
    for r in raw_samples:
        by_intent[r["intent"]].append(r)

    train, val, test = [], [], []

    for intent, items in by_intent.items():
        random.shuffle(items)
        n = len(items)
        n_train = int(n * ratios[0])
        n_val   = int(n * ratios[1])

        train.extend(items[:n_train])
        val.extend(items[n_train:n_train+n_val])
        test.extend(items[n_train+n_val:])

    return train, val, test

# def stratified_split(samples_by_intent: dict, ratios=(0.8, 0.1, 0.1)):
#     train, val, test = [], [], []
#     for intent, items in samples_by_intent.items():
#         random.shuffle(items)
#         n = len(items)
#         n_train = int(n * ratios[0])
#         n_val   = int(n * ratios[1])
#         train.extend(items[:n_train])
#         val.extend(items[n_train:n_train + n_val])
#         test.extend(items[n_train + n_val:])
#     return train, val, test

# 고친 부분. 테스트 안섞이게
def main(input_path: str, output_dir: str, seed: int = 42):
    random.seed(seed)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    raw_samples = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    raw_samples.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"[SKIP] JSON 파싱 오류: {e}")

    print(f"원본 샘플 수: {len(raw_samples)}")

    # ✅ 1️⃣ utterance 단위 stratified split
    train_raw, val_raw, test_raw = stratified_split_raw(raw_samples)

    print(f"Raw split → Train:{len(train_raw)} Val:{len(val_raw)} Test:{len(test_raw)}")

    # ✅ 2️⃣ 각 split별 flatten
    def flatten_list(raw_list):
        flat = []
        for r in raw_list:
            flat.extend(flatten_sample(r))
        return flat

    train = flatten_list(train_raw)
    val   = flatten_list(val_raw)
    test  = flatten_list(test_raw)

    print(f"Flatten 후 → Train:{len(train)} Val:{len(val)} Test:{len(test)}")

    # 저장
    for split_name, split_data in [("train", train), ("val", val), ("test", test)]:
        out_path = Path(output_dir) / f"{split_name}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in split_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"→ {out_path} 저장 완료")

    # registry 저장
    registry_path = Path(output_dir) / "slot_registry.json"
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(SLOT_REGISTRY, f, ensure_ascii=False, indent=2)
    print(f"→ {registry_path} 저장 완료")

# def main(input_path: str, output_dir: str, seed: int = 42):
#     random.seed(seed)
#     Path(output_dir).mkdir(parents=True, exist_ok=True)

#     raw_samples = []
#     with open(input_path, "r", encoding="utf-8") as f:
#         for line in f:
#             line = line.strip()
#             if line:
#                 try:
#                     raw_samples.append(json.loads(line))
#                 except json.JSONDecodeError as e:
#                     print(f"  [SKIP] JSON 파싱 오류: {e} → {line[:80]}")

#     print(f"원본 샘플 수: {len(raw_samples)}")

#     all_flat = []
#     for raw in raw_samples:
#         all_flat.extend(flatten_sample(raw))

#     print(f"Flatten 후 샘플 수: {len(all_flat)}")

#     # NONE/ACTIVE 비율 확인
#     from collections import Counter
#     status_count = Counter(s["status"] for s in all_flat)
#     print(f"Status 분포: {dict(status_count)}")

#     by_intent = defaultdict(list)
#     for s in all_flat:
#         by_intent[s["intent"]].append(s)

#     train, val, test = stratified_split(by_intent)
#     print(f"Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")

#     for split_name, split_data in [("train", train), ("val", val), ("test", test)]:
#         out_path = Path(output_dir) / f"{split_name}.jsonl"
#         with open(out_path, "w", encoding="utf-8") as f:
#             for item in split_data:
#                 f.write(json.dumps(item, ensure_ascii=False) + "\n")
#         print(f"  → {out_path} 저장 완료")

#     registry_path = Path(output_dir) / "slot_registry.json"
#     with open(registry_path, "w", encoding="utf-8") as f:
#         json.dump(SLOT_REGISTRY, f, ensure_ascii=False, indent=2)
#     print(f"  → {registry_path} 저장 완료")


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input",  nargs="?", default="data.jsonl")
    parser.add_argument("output", nargs="?", default="data")
    parser.add_argument("--eval", action="store_true",
                        help="split 없이 전체를 test.jsonl 하나로 저장 (일반화 평가용)")
    args = parser.parse_args()

    if args.eval:
        # ── eval 모드: flatten만 하고 전체를 test.jsonl로 저장 ──────────────
        random.seed(42)
        Path(args.output).mkdir(parents=True, exist_ok=True)

        raw_samples = []
        with open(args.input, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        raw_samples.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"  [SKIP] JSON 파싱 오류: {e} → {line[:80]}")

        print(f"원본 샘플 수: {len(raw_samples)}")

        all_flat = []
        for raw in raw_samples:
            all_flat.extend(flatten_sample(raw))

        print(f"Flatten 후 샘플 수: {len(all_flat)}")

        from collections import Counter
        status_count = Counter(s["status"] for s in all_flat)
        print(f"Status 분포: {dict(status_count)}")

        out_path = Path(args.output) / "test.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in all_flat:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"  → {out_path} 저장 완료 ({len(all_flat)}개)")

    else:
        main(args.input, args.output)