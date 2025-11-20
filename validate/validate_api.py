from urllib.parse import urlparse, parse_qs
from validate.whitelist_prefix import PRIORITY_PREFIXES
from validate.param_rules import validate_param

def validate_api(api: str):
    """
    LLM이 반환한 API 문자열이:
    1) prefix whitelist 에 포함되는지
    2) 파라미터 규칙이 유효한지
    검증 후 OK면 그대로 반환, 아니면 /NO_FUNCTION 반환
    """

    api = api.strip()

    # NO_FUNCTION은 그대로 허용
    if api == "/NO_FUNCTION":
        return api

    # 1) Prefix whitelist 검사
    if not any(api.startswith(prefix) for prefix in PRIORITY_PREFIXES):
        return "/NO_FUNCTION"

    # 2) 파라미터가 없는 API는 그대로 통과
    if "?" not in api:
        return api

    # 3) 파라미터 파싱
    parsed = urlparse(api)
    query_params = parse_qs(parsed.query)

    # 4) key/value 구조 검사
    for key, val in query_params.items():
        value = val[0]  # parse_qs는 리스트로 반환하므로 첫번째 값만 사용

        if not validate_param(key, value):
            return "/NO_FUNCTION"

    return api
