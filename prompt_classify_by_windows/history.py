from common_prompt import build_prompt

HISTORY_SPECIFIC = """
## history 창 값 변경 및 업데이트
- `/history/update?propertyName=date&value=YYYY-MM-DD_YYYY-MM-DD` : 특정 날짜의 검사 기록. 단, YYYY-MM-DD 대신 실제 날짜를 넣어야 해. 
(예시: 이번달 기록 보여줘 /history/update?propertyName=date&value=2025-09-01_2025-09-30),
(예시: 250901-251101 기록 /history/update?propertyName=date&value=2025-09-01_2025-11-01)

- `/history/update?propertyName=camera&value=status` : 기록 창에서 카메라 필터 설정. (status=다음 중 하나: `NotSelected`, `Mapping`, `SettingX1`, `SettingX2`, `PRS`, `BarCode`, `TopBarCode`, `Side` )
- `/history/update?propertyName=inspection&value=status` : 기록 창에서 검사 필터 설정. (status=다음 중 하나: `NotSelected`, `Mapping`, `Mark`, `Qfn`, `Bga`, `Lga`, `DataCode`, `BottomDataCode` , `Strip` )
- `/history/update?propertyName=BUTTON&value=status` : 기록 창에서 검사 필터 설정. (status=다음 중 하나: `save`, `open`)

"""

system_prompt = build_prompt(HISTORY_SPECIFIC)