from common_prompt import build_prompt

CALIBRATION_SPECIFIC = """

## calibration 창 값 변경 및 업데이트
- `/calibration/update?propertyName=button&value=status` : 보정(캘리브레이션) 창에서 특정 버튼 클릭 (status=다음 중 하나: `Test`, `LightSave`)
- `/calibration/update?propertyName=tab&value=status` : 보정(캘리브레이션) 창에서 특정 탭 클릭 (status=다음 중 하나: `bottom`, `setting`,`pad`,'tray','vision')
- `/calibration/update?propertyName=roi&value=status` : 보정(캘리브레이션) 창에서 로이 생성 혹은 초기화(재생성) (status =다음 중 하나: `create`, `recreate`)
- `/calibration/update?propertyName=threshold&value=minN-maxN` : 보정(캘리브레이션) 창에서 임계값 설정 (예시: 임계값 100-200 /calibration/parameter?threshold=100-200, 임계값 초기화 /calibration/parameter?threshold=0-255)
- `/calibration/update?propertyName=size&value=minN-maxN` : 보정(캘리브레이션) 창에서 사이즈 설정 (예시: 사이즈 1-500 /calibration/parameter?size=1-500, 사이즈 초기화 /calibration/parameter?size=1-999999)
- `/calibration/update?propertyName=shape&value=status-N` : 보정(캘리브레이션) 창에서 유사도 설정 (status는 다음 중 하나: `rectangle`, `circle`)(N은 Similarity 숫자)(예시: 모양 원, 60 /calibration/update?propertyName=shape&value=circle-60)
- `/calibration/update?propertyName=select&value=status` : 보정(캘리브레이션) 창에서 기준 설정 (status는 다음 중 하나: `MULTIOBJECT`, `CENTER`, `BIGGEST`)
- `/calibration/update?propertyName=RETICLETYPE&value=status` : 보정(캘리브레이션) 창에서 십자선 타입 설정 (status는 다음 중 하나: `NONE`, `DEFAULT`, `FULLSIZE`)
- `/calibration/update?propertyName=camera&value=status` : 보정(캘리브레이션) 창에서 카메라 변경 (status는 다음 중 하나: `)

"""
system_prompt = build_prompt(CALIBRATION_SPECIFIC)