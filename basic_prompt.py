from common_prompt import build_prompt

# 기본 프롬프트 (창이 열려있지 않을 때 사용)
# 레시피 관련 API들
SPECIFIC_CONTENT = """
## 단순 창 열기
- `/windows/teaching/lga` : LGA 티칭 창 열기
- `/windows/teaching/qfn` : QFN 티칭 창 열기
- `/windows/teaching/bga` : BGA 티칭 창 열기
- `/windows/teaching/mapping` : MAPPING 티칭 창 열기
- `/windows/teaching/strip` : Strip 티칭 창 열기
- `/windows/history` : 검사 기록 창 열기
- `/windows/light` : 조명 설정 창 열기
- `/windows/calibration` : 보정(캘리브레이션) 창 열기
- `/windows/settings` : 설정창 열기, 레시피, 레시피 창 열기
- `/windows/lot` : lot data 창 열기
...
"""

# 공통 프롬프트 + 특화 프롬프트 결합
system_prompt = build_prompt() # 겹치는 부분이라서 인자 일단 뺌.
# system_prompt = build_prompt(SPECIFIC_CONTENT)