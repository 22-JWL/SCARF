"""
slot_url_builder.py
인텐트 + 슬롯 → API URL 변환기
"""

_TEACHING_WINDOWS = {"lga", "qfn", "bga", "mapping", "strip"}

_OPEN_WINDOW_MAP = {
    "lga":         "/windows/teaching/lga",
    "qfn":         "/windows/teaching/qfn",
    "bga":         "/windows/teaching/bga",
    "mapping":     "/windows/teaching/mapping",
    "strip":       "/windows/teaching/strip",
    "history":     "/windows/history",
    "light":       "/windows/light",
    "calibration": "/windows/calibration",
    "setting":     "/windows/settings",
    "settings":    "/windows/settings",
    "lot":         "/windows/lot",
}


def _base_path(window_name: str) -> str:
    """창 이름을 기반으로 update API의 base path를 반환."""
    w = (window_name or "").lower()
    if w in _TEACHING_WINDOWS:
        return f"/teaching/{w}/update"
    if w == "calibration":
        return "/calibration/update"
    if w == "history":
        return "/history/update"
    if w in ("setting", "settings"):
        return "/settings/update"
    # 알 수 없는 창이면 teaching으로 fallback
    return f"/teaching/{w}/update"


def build_url_from_slots(intent: str, slots: dict) -> str:
    """
    인텐트와 채워진 슬롯으로 API URL을 구성한다.

    Args:
        intent: 분류된 인텐트 (e.g., "set_threshold")
        slots:  DSTManager가 채운 슬롯 dict (e.g., {"window_name": "lga", ...})

    Returns:
        API URL 문자열 (e.g., "/teaching/lga/update?propertyName=ScratchThreshold&value=100")
    """
    window = (slots.get("window_name") or "").lower()

    # ── open_window ─────────────────────────────────────────────────────────
    if intent == "open_window":
        return _OPEN_WINDOW_MAP.get(window, f"/windows/{window}")

    # ── change_operation ─────────────────────────────────────────────────────
    if intent == "change_operation":
        return f"/mode/set?mode={slots.get('operation', 'RUN')}"

    # ── set_threshold ────────────────────────────────────────────────────────
    if intent == "set_threshold":
        base = _base_path(window)
        return (f"{base}?propertyName={slots.get('threshold_type', '')}"
                f"&value={slots.get('threshold_value', '')}")

    # ── set_size ─────────────────────────────────────────────────────────────
    if intent == "set_size":
        base = _base_path(window)
        return (f"{base}?propertyName={slots.get('size_type', '')}"
                f"&value={slots.get('size_value', '')}")

    # ── set_option ───────────────────────────────────────────────────────────
    if intent == "set_option":
        base = _base_path(window)
        return (f"{base}?propertyName={slots.get('option_type', '')}"
                f"&value={slots.get('option_value', '')}")

    # ── set_parameter ────────────────────────────────────────────────────────
    if intent == "set_parameter":
        base = _base_path(window)
        return (f"{base}?propertyName={slots.get('parameter_name', '')}"
                f"&value={slots.get('parameter_value', '')}")

    # ── geometry_set ─────────────────────────────────────────────────────────
    if intent == "geometry_set":
        base = _base_path(window)
        return (f"{base}?propertyName={slots.get('geometry_position', '')}"
                f"&value={slots.get('coordinate_value', '')}")

    # ── roi_collection_control ───────────────────────────────────────────────
    if intent == "roi_collection_control":
        base = _base_path(window)
        return (f"{base}?propertyName={slots.get('roi_type', '')}"
                f"&value={slots.get('roi_action', '')}")

    # ── inspection_execute ───────────────────────────────────────────────────
    if intent == "inspection_execute":
        base = _base_path(window)
        return f"{base}?propertyName={slots.get('inspection_type', '')}&value=execute"

    # ── auto_configuration_execute ───────────────────────────────────────────
    if intent == "auto_configuration_execute":
        base = _base_path(window)
        return f"{base}?propertyName={slots.get('auto_type', '')}&value=execute"

    # ── ui_navigation_execute ────────────────────────────────────────────────
    if intent == "ui_navigation_execute":
        if window == "light":
            return f"/windows/light/live?camera={slots.get('camera_type', '')}"
        base = _base_path(window)
        return f"{base}?propertyName=tabChange&value={slots.get('tab_name', '')}"

    # ── system_setting ───────────────────────────────────────────────────────
    if intent == "system_setting":
        if "settingNumPropertyName" in slots:
            return (f"/settings/update?propertyName={slots['settingNumPropertyName']}"
                    f"&value={slots.get('settingNumValue', '')}")
        if "settingBoolPropertyName" in slots:
            return (f"/settings/update?propertyName={slots['settingBoolPropertyName']}"
                    f"&value={slots.get('settingBoolValue', '')}")
        if "settingColorPropertyName" in slots:
            return (f"/settings/update?propertyName={slots['settingColorPropertyName']}"
                    f"&value={slots.get('setColorValue', '')}")
        return "/NO_FUNCTION"

    # ── calibration_control ──────────────────────────────────────────────────
    if intent == "calibration_control":
        action_type = slots.get("action_type", "")
        if action_type == "button":
            return f"/calibration/update?propertyName=button&value={slots.get('button_action', '')}"
        if action_type == "shape_similarity":
            return (f"/calibration/update?propertyName=shapeSimilarity"
                    f"&value={slots.get('shape_type', '')},{slots.get('similarity_value', '')}")
        if action_type == "reference_select":
            return f"/calibration/update?propertyName=referenceSelect&value={slots.get('reference_type', '')}"
        if action_type == "reticle_type":
            return f"/calibration/update?propertyName=reticleType&value={slots.get('reticle_type', '')}"
        if action_type == "camera":
            return f"/calibration/update?propertyName=camera&value={slots.get('camera_type', '')}"
        return "/NO_FUNCTION"

    # ── history_control ──────────────────────────────────────────────────────
    if intent == "history_control":
        filter_type = slots.get("filter_type", "")
        if filter_type == "date":
            return f"/history/update?propertyName=dateRange&value={slots.get('date_range', '')}"
        if filter_type == "camera":
            return f"/history/update?propertyName=camera&value={slots.get('camera_type', '')}"
        if filter_type == "inspection":
            return (f"/history/update?propertyName=inspectionType"
                    f"&value={slots.get('history_inspection_type', '')}")
        if filter_type == "button":
            return f"/history/update?propertyName=button&value={slots.get('button_action', '')}"
        return "/NO_FUNCTION"

    # ── recipe_management ────────────────────────────────────────────────────
    if intent == "recipe_management":
        action = slots.get("action", "")
        recipe = slots.get("recipe_name", "")
        target = slots.get("target_name", "")
        if action == "add":
            return f"/recipes/add?name={recipe}"
        if action == "copy":
            return f"/recipes/copy?source={recipe}&dest={target}"
        if action == "rename":
            return f"/recipes/rename?old={recipe}&new={target}"
        if action == "delete":
            return f"/recipes/delete?name={recipe}"
        if action == "select":
            return f"/recipes/select?name={recipe}"
        return "/NO_FUNCTION"

    return "/NO_FUNCTION"
