from common_prompt import build_prompt

MAPPING_SPECIFIC = """
## mapping 티칭 창 값 변경 및 업데이트
### mapping 티칭 창 임계값 변경
-`/teaching/mapping/update?propertyName=MarkThreshold&value=N-N` : mapping 티칭 창 Mark 탭에서 임계값 설정(N 은 숫자)
-`/teaching/mapping/update?propertyName=ScratchThreshold&value=N-N` : mapping 티칭 창 임계값 설정(N 은 숫자)
-`/teaching/mapping/update?propertyName=ForeignMaterialThreshold&value=N-N` : mapping 티칭 창 임계값 설정(N 은 숫자)
-`/teaching/mapping/update?propertyName=ContaminationThreshold&value=N-N` : mapping  티칭 창 임계값 설정(N 은 숫자)
-`/teaching/mapping/update?propertyName=OutlineThreshold&value=N-N` : mapping 티칭 창 sawing 탭 임계값 설정(N 은 숫자)
-`/teaching/mapping/update?propertyName=RejectMarkThreshold&value=N-N` : mapping 티칭 창 RejectMark 탭에서 임계값 설정(N 은 숫자)
(예시: mapping창 Scratch 임계값 2-33, /teaching/mapping/update?propertyName=ScratchThreshold&value=2-33)

### mapping 티칭 창 사이즈값 변경
-`/teaching/mapping/update?propertyName=ScratchSize&value=N-N` : mapping 티칭 창 Scratch 탭 사이즈 설정(N 은 숫자)
-`/teaching/mapping/update?propertyName=ForeignMaterialSize&value=N-N` : mapping 티칭 창 ForeignMaterial 사이즈 설정(N 은 숫자)
-`/teaching/mapping/update?propertyName=ContaminationSize&value=N-N` : mapping 티칭 창 Contamination 사이즈 설정(N 은 숫자)
-`/teaching/mapping/update?propertyName=RejectMarkSize&value=N-N` : mapping 티칭 창 RejectMark 탭 사이즈 설정(N 은 숫자)

### mapping 티칭 테스트
- `/teaching/mapping/update?propertyName=findPackagesTeaching&value=1` : mapping 티칭 창에서 티칭 테스트 
- `/teaching/mapping/update?propertyName=inspectMarksAndDataCodeTeaching&value=1` : mapping 티칭 창에서 티칭 테스트
- `/teaching/mapping/update?propertyName=inspectSurfaceTeaching&value=1` : mapping 티칭 창에서 티칭 테스트
- `/teaching/mapping/update?propertyName=inspectSawingTeaching&value=1` : mapping 티칭 창에서 티칭 테스트 
- `/teaching/mapping/update?propertyName=inspectRejectMarkTeaching&value=1` : mapping 티칭 창에서 티칭 테스트 
- `/teaching/mapping/update?propertyName=inspectTeaching&value=1` : mapping 티칭 창 result 탭에서 티칭 테스트 

### mapping 티칭 창 탭 이동
- `/teaching/mapping/update?propertyName=moveTab&value=status` : LGA 티칭 창에서 특정 탭으로 이동 (status는 다음 중 하나: `Package`, `Mark`, `Surface`, `Sawing`, `RejectMark`, `DontCare`, `Result`)

### mapping 티칭 창 roi 단일 생성 버튼
- `/teaching/mapping/update?propertyName=GridRoi_&value=N-N-N-N` : mapping 티칭 창 package 탭에서 ROI 생성
- `/teaching/mapping/update?propertyName=CodeRoi_&value=N-N-N-N` : mapping 티칭 창 Mark 탭에서 ROI 생성
- `/teaching/mapping/update?propertyName=RejectMarkRoi_&value=N-N-N-N` : mapping 티칭 창 RejectMark 탭에서 ROI 생성
(예시: mapping 창 model RejectMark roi 10-20-30-40, /teaching/mapping/update?propertyName=RejectMarkRoi_&value=10-20-30-40)
(예시2: mapping 창 model RejectMark roi 생성, /teaching/mapping/update?propertyName=PackageModelRoi_&value=1)

### mapping 티칭 창 ROI 생성/삭제/초기화/읽기 버튼
- `/teaching/mapping/update?propertyName=MarkRoi&value=status` : mapping 티칭 창 Mark 탭 ROI 추가,삭제,초기화 
- `/teaching/mapping/update?propertyName=DontCareRoi&value=status` : mapping 티칭 창 DontCare 탭 ROI 추가,삭제,초기화 
- `/teaching/mapping/update?propertyName=SurfaceRoi&value=status` : mapping 티칭 창 Surface 탭 ROI 추가,삭제,초기화 
(status는 다음 중 하나: `add`, `delete`, `reset`, `read`)
,(예시: mapping 창 surface 탭 roi add, /teaching/mapping/update?propertyName=SurfaceRoi&value=add)

### mapping 티칭 창 roi, threshold 자동 생성 버튼
- `/teaching/mapping/update?propertyName=autoThresholdCommand&value=1` : mapping 티칭 창에서 임계값 자동 설정

### mapping combobox 값 변경
- `/teaching/mapping/update?propertyName=PackageEdgeDetectDirection&value=status` : mapping 티칭 창 edge 방향값 변경(status는 다음 중 하나: `InToOut`, `OutToIn`)
- `/teaching/mapping/update?propertyName=PackageEdgeDetectMode&value=status` : mapping 티칭 창 edge 모드 변경 (status는 다음 중 하나: `BlackToWhite`, `WhiteToBlack`)

### mapping 값 변경
- `/teaching/mapping/update?propertyName=OutlineWidth&value=N` : 외곽선 너비(N은 숫자)
- `/teaching/mapping/update?propertyName=PackageThresholdDiff&value=N` : Edge Threshold Amplitude 값 설정(N은 숫자)
- `/teaching/mapping/update?propertyName=RotateAngle&value=N` : 회전 각도 값 설정(N은 숫자, 다음중 하나: 0, 90, 180, 270)
- `/teaching/mapping/update?propertyName=Row-Column&value=N-N` : 가로 세로 값 변경(N-N 은 숫자)

"""

system_prompt = build_prompt(MAPPING_SPECIFIC)