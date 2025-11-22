from common_prompt import build_prompt

QFN_SPECIFIC = """
## qfn 티칭 창 값 변경 및 업데이트
### qfn 티칭 창 임계값 변경
-`/teaching/qfn/update?propertyName=PackageThreshold&value=N-N` : qfn 티칭 창 package 탭에서 임계값 설정(N 은 숫자)
-`/teaching/qfn/update?propertyName=FirstPinThreshold&value=N-N` : qfn 티칭 창 package FirstPin 임계값 설정(N 은 숫자)
-`/teaching/qfn/update?propertyName=PadThreshold&value=N-N` : qfn 티칭 창 Pad 탭에서 임계값 설정(N 은 숫자)
-`/teaching/qfn/update?propertyName=LeadThreshold&value=N-N` : qfn 티칭 창 Lead 탭에서 임계값 설정(N 은 숫자)
-`/teaching/qfn/update?propertyName=ScratchThreshold&value=N-N` : qfn 티칭 창 Scratch 임계값 설정(N 은 숫자)
-`/teaching/qfn/update?propertyName=ForeignMaterialThreshold&value=N-N` : qfn 티칭 창 ForeignMaterial 임계값 설정(N 은 숫자)
-`/teaching/qfn/update?propertyName=ContaminationThreshold&value=N-N` : qfn 티칭 창 Contamination 임계값 설정(N 은 숫자)
-`/teaching/qfn/update?propertyName=OutlineThreshold&value=N-N` : qfn 티칭 창 sawing 탭에서 임계값 설정(N 은 숫자)
-`/teaching/qfn/update?propertyName=RejectMarkThreshold&value=N-N` : qfn 티칭 창 RejectMark 탭에서 임계값 설정(N 은 숫자)
(예시: qfn 창 package 탭에서 임계값 2-33, /teaching/qfn/update?propertyName=PackageThreshold&value=2-33)

### qfn 티칭 창 사이즈값 변경
-`/teaching/qfn/update?propertyName=LeadContaminationSize&value=N-N` : qfn 티칭 창 Lead 탭 사이즈 설정(N 은 숫자)
-`/teaching/qfn/update?propertyName=ScratchSize&value=N-N` : qfn 티칭 창 Scratch 탭 사이즈 설정(N 은 숫자)
-`/teaching/qfn/update?propertyName=ForeignMaterialSize&value=N-N` : qfn 티칭 창 ForeignMaterial 사이즈 설정(N 은 숫자)
-`/teaching/qfn/update?propertyName=ContaminationSize&value=N-N` : qfn 티칭 창 Contamination 사이즈 설정(N 은 숫자)
-`/teaching/qfn/update?propertyName=RejectMarkSize&value=N-N` : qfn 티칭 창 RejectMark 탭 사이즈 설정(N 은 숫자)

### qfn 티칭 창 ROI 생성/삭제/초기화 버튼
- `/teaching/qfn/update?propertyName=LeadRois&value=status` : qfn 티칭 창 Lead 탭 ROI 추가,삭제,초기화 
- `/teaching/qfn/update?propertyName=SurfaceRoi&value=status` : qfn 티칭 창 Surface 탭 ROI 추가,삭제,초기화 
- `/teaching/qfn/update?propertyName=DontCareRoi&value=status` : qfn 티칭 창 DontCare 탭 ROI 추가,삭제,초기화 
(status는 다음 중 하나: `add`, `delete`, `reset`)
,(예시: qfn 창 lead 탭 roi add, /teaching/qfn/update?propertyName=LeadRois&value=add)

### qfn 티칭 창 roi, threshold 자동 생성 버튼
- `/teaching/qfn/update?propertyName=findPackageRoiAutoCommand&value=1` : qfn 티칭 창에서 ROI 자동 생성
- `/teaching/qfn/update?propertyName=findAutoThresholdCommand&value=1` : qfn 티칭 창에서 임계값 자동 설정

### qfn 티칭 창 roi 단일 생성 버튼
- `/teaching/qfn/update?propertyName=PackageRoiTop_&value=N-N-N-N` : qfn 티칭 창 해당 탭에서 ROI 생성 
- `/teaching/qfn/update?propertyName=PackageRoiLeft_&value=N-N-N-N` : qfn 티칭 창 해당 탭에서 ROI 생성 
- `/teaching/qfn/update?propertyName=PackageRoiBottom_&value=N-N-N-N` : qfn 티칭 창 해당 탭에서 ROI 생성 
- `/teaching/qfn/update?propertyName=PackageRoiRight_&value=N-N-N-N` : qfn 티칭 창 해당 탭에서 ROI 생성 
- `/teaching/qfn/update?propertyName=PackageModelRoi_&value=N-N-N-N` : qfn 티칭 창 해당 탭에서 ROI 생성 
- `/teaching/qfn/update?propertyName=FirstPinRoi_&value=N-N-N-N` : qfn 티칭 창 해당 탭에서 ROI 생성 
- `/teaching/qfn/update?propertyName=PadRoi_&value=N-N-N-N` : qfn 티칭 창 해당 탭에서 ROI 생성 
- `/teaching/qfn/update?propertyName=RejectMarkRoi_&value=N-N-N-N` : qfn 티칭 창 해당 탭에서 ROI 생성 
(예시: qfn 창 model roi 10-20-30-40, /teaching/qfn/update?propertyName=PackageModelRoi_&value=10-20-30-40)
(예시2: qfn 창 Package Roi Top 생성, /teaching/qfn/update?propertyName=PackageModelRoi_&value=1)

### qfn 티칭 테스트
- `/teaching/qfn/update?propertyName=inspectPackageTeaching&value=1` : qfn 티칭 창에서 티칭 테스트 
- `/teaching/qfn/update?propertyName=inspectPadAndLeadsTeaching&value=1` : qfn 티칭 창에서 티칭 테스트
- `/teaching/qfn/update?propertyName=inspectSurfaceTeaching&value=1` : qfn 티칭 창에서 티칭 테스트
- `/teaching/qfn/update?propertyName=inspectSawingTeaching&value=1` : qfn 티칭 창에서 티칭 테스트 
- `/teaching/qfn/update?propertyName=inspectRejectMarkTeaching&value=1` : qfn 티칭 창에서 티칭 테스트 

### qfn combobox 값 변경
- `/teaching/qfn/update?propertyName=PackageEdgeDetectDirection&value=status` : qfn 티칭 창 edge 방향값 변경(status는 다음 중 하나: `InToOut`, `OutToIn`)
- `/teaching/qfn/update?propertyName=PackageEdgeDetectMode&value=status` : qfn 티칭 창 edge 모드 변경 (status는 다음 중 하나: `BlackToWhite`, `WhiteToBlack`)

### qfn 티칭 창 탭 이동
- `/teaching/qfn/update?propertyName=moveTab&value=status` : qfn 티칭 창에서 특정 탭으로 이동 (status는 다음 중 하나: `Package`, `padLeads`, `Surface`, `Sawing`, `RejectMark`, `DontCare`, `Result`)

### qfn 값 변경
- `/teaching/qfn/update?propertyName=OutlineWidth&value=N` : 외곽선 너비(N은 숫자)
- `/teaching/qfn/update?propertyName=PackageThresholdDiff&value=N` : Edge Threshold Amplitude 값 설정(N은 숫자)
- `/teaching/lga/update?propertyName=FirstPinType&value=status` : LGA 티칭 창에서 첫 번째 핀 타입 속성 업데이트(status는 다음 중 하나:  `SmallPad`, `Notch`, `Chamfer`)

"""

system_prompt = build_prompt(QFN_SPECIFIC)