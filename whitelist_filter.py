import re
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

#파일에서 URL 추출하고, 임의로 부여된 임계값 무시한 whitelist 생성
def create_url_whitelist(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        system_prompt_text = f.read()

    url_pattern = r'`?(/[\w/=?&\[\]\{\}"-]+)`?'
    urls = set(re.findall(url_pattern, system_prompt_text))

    def normalize(url: str) -> str:
        parsed = urlparse(url)
        query_params = parse_qsl(parsed.query, keep_blank_values=True)

        # 임계값 조정 변수
        keys_to_ignore = {"value", "size", "threshold", "no"}
        normalized_params = [(k, "" if k in keys_to_ignore else v) for k, v in query_params]
        normalized_query = urlencode(normalized_params)
        
        normalized_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            normalized_query,
            parsed.fragment
        ))
        return normalized_url if normalized_query else parsed.path

    whitelist = {normalize(u) for u in urls}

    def is_valid_api_safe(input_url: str) -> bool:
        return normalize(input_url) in whitelist

    #검사용 함수 반환
    return is_valid_api_safe