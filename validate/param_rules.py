import re
import json

# -----------------------
# 기본 유효성 검사용 함수들
# -----------------------

def is_number(val):
    """정수인지 검사"""
    return re.fullmatch(r"\d+", val) is not None

def is_number_pair(val):
    """N-N 구조인지 검사"""
    return re.fullmatch(r"\d+-\d+", val) is not None

def is_allowed_status(val):
    """add/delete/reset/read 등 지정된 문자열"""
    return val.lower() in ["add", "delete", "reset", "read"]

def is_camera_type(val):
    """카메라 종류 whitelist"""
    return val in ["PRS", "BarCode", "SettingX1", "SettingX2", "Mapping"]

def is_json_roi(val):
    """ROI JSON 형태 검사"""
    try:
        obj = json.loads(val)
        return all(k in obj for k in ["Row1", "Column1", "Row2", "Column2"])
    except:
        return False

# -----------------------
# 파라미터 key별 검사 로직
# -----------------------

def validate_param(key, value):
    """value 형식 검사"""
    if key == "value":
        if is_number_pair(value):   # N-N
            return True
        if is_number(value):        # N
            return True
        if is_allowed_status(value):  # add/delete/reset 등
            return True
        if is_camera_type(value):     # 카메라 명
            return True
        if value.startswith("{"):     # JSON ROI
            return is_json_roi(value)
        if value in ["0", "1"]:       # 0/1
            return True

        return False  # 나머지는 모두 차단

    return True  # value 이외는 특별 검사 없음
