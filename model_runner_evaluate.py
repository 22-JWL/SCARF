"""
재현도/정확도 평가용 LLM 호출 래퍼.

핵심 목적
- app.py에서 사용하는 run_model()을 100% 동일한 방식으로 호출한다.
- run_model()은 dict를 반환하므로, 반드시 dict["output"]을 문자열로 추출해야 한다.
"""

from typing import Dict, Optional
from model_runner import run_model, DEFAULT_MODEL_NAME


def run_model_evaluate(
    text: str,
    model_name: str = DEFAULT_MODEL_NAME,
    current_opened_window_and_tab: Optional[Dict[str, str]] = None,
) -> str:
    """
    재현도 평가용 LLM 호출 함수.
    app.py와 100% 동일한 호출 구조를 유지해야 한다.
    """

    # 평가용에서는 상태 없으므로 빈 dict 사용
    if current_opened_window_and_tab is None:
        current_opened_window_and_tab = {}

    # ⚠ 절대 파라미터 순서를 바꾸면 안 됨 (app.py와 동일)
    # app.py 내부:
    #   result = run_model(user_input, current_window_info, model_name)
    result = run_model(
        text,
        current_opened_window_and_tab,   # 2nd
        model_name,                      # 3rd
    )

    # ⚠ run_model 은 dict 반환 → output 문자열만 추출
    if isinstance(result, dict):
        return result.get("output", "")
    else:
        return str(result)
