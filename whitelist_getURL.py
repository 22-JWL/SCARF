'''

### BGA 티칭 창 임계값 변경
-`/teaching/bga/update?propertyName=PackageThreshold&value=N-N` : BGA 티칭 창 package 탭에서 임계값 설정(N 은 숫자)
-`/teaching/bga/update?propertyName=ScratchThreshold&value=N-N` : BGA 티칭 창 Scratch 임계값 설정(N 은 숫자)
-`/teaching/bga/update?propertyName=ForeignMaterialThreshold&value=N-N` : BGA 티칭 창 ForeignMaterial 임계값 설정(N 은 숫자)
-`/teaching/bga/update?propertyName=ContaminationThreshold&value=N-N` : BGA 티칭 창 Contamination 임계값 설정(N 은 숫자)
-`/teaching/bga/update?propertyName=OutlineThreshold&value=N-N` : BGA 티칭 창 sawing 탭에서 Outline 임계값 설정(N 은 숫자)
-`/teaching/bga/update?propertyName=RejectMarkThreshold&value=N-N` : BGA 티칭 창 RejectMark 탭에서 임계값 설정(N 은 숫자)

### BGA 티칭 창 탭 이동
- `/teaching/bga/update?propertyName=moveTab&value=status` : BGA 티칭 창에서 특정 탭으로 이동 (status는 다음 중 하나: `Package`, `FirstPinPattern`, `Ball`, `Surface`, `Sawing`, `RejectMark`, `DontCare`, `Result`)

### BGA Package 탭
- `/teaching/bga/update?propertyName=PackageRoiTop_&value=N-N-N-N` : Package 외곽 ROI (상단)
- `/teaching/bga/update?propertyName=PackageRoiBottom_&value=N-N-N-N` : Package 외곽 ROI (하단)
- `/teaching/bga/update?propertyName=PackageRoiLeft_&value=N-N-N-N` : Package 외곽 ROI (좌측)
- `/teaching/bga/update?propertyName=PackageRoiRight_&value=N-N-N-N` : Package 외곽 ROI (우측)
- `/teaching/bga/update?propertyName=PackageThreshold&value=N-N` : BGA 티칭 창 package 탭에서 임계값 설정(N 은 숫자)
- `/teaching/bga/update?propertyName=PackageEdgeDetectDirection&value=status` : BGA 티칭 창 edge 방향값 변경(status는 다음 중 하나: `InToOut`, `OutToIn`)
- `/teaching/bga/update?propertyName=PackageEdgeDetectMode&value=status` : BGA 티칭 창 edge 모드 변경 (status는 다음 중 하나: `BlackToWhite`, `WhiteToBlack`)
- `/teaching/bga/update?propertyName=PackageThresholdDiff&value=N` : Edge Threshold Amplitude 값 설정
- `/teaching/bga/update?propertyName=PackageModelRoi_&value=N-N-N-N` : Package 모델 ROI
- `/teaching/bga/update?propertyName=findPackageRoiAutoTeaching&value=1` : BGA 티칭창 Package탭에서 Auto ROI 버튼 클릭
- `/teaching/bga/update?propertyName=findAutoThresholdTeaching&value=1` :  BGA 티칭창 Package탭에서 AutoThreshold 버튼 클릭
- `/teaching/bga/update?propertyName=inspectPackageTeaching&value=1` : BGA 티칭창 Package탭에서 Find Package 버튼 클릭

### BGA FirstPin/Pattern 탭
# - `/teaching/bga/update?propertyName=FirstPinRoi_&value=N-N-N-N` : First Pin ROI
- `/teaching/bga/update?propertyName=FirstPinThreshold&value=N-N` : BGA 티칭 창 FirstPin/Pattern 탭에서 FirstPin 임계값 설정(N 은 숫자)
# - `/teaching/bga/update?propertyName=PatternRois&value=status` : bga roi 설정 (status는 다음 중 하나: `add`, `delete`, `reset`)
-`/teaching/bga/update?propertyName=PatternThreshold&value=N-N` : BGA 티칭 창 FirstPin/Pattern 탭에서 Pattern 임계값 설정(N 은 숫자)
-`/teaching/bga/update?propertyName=findFirstPinAndPatternTeaching&value=1` : findPattern and FirstPin 버튼 클릭(N 은 숫자)

### BGA Ball 탭
# - `/teaching/bga/update?propertyName=BallRois&value=status` : Ball ROI (status는 다음 중 하나: `add`, `delete`, `reset`)
- `/teaching/bga/update?propertyName=BallThreshold&value=N-N` : BGA 티칭 창 Ball 탭에서 임계값 설정(N 은 숫자)
- `/teaching/bga/update?propertyName=BallPositionOffset&value=N` : Ball Offset Tolerance 설정(N 은 숫자)
- `/teaching/bga/update?propertyName=BallMinCircularity&value=N` : Ball Min Circularity 퍼센트 설정(N은 숫자)
- `/teaching/bga/update?propertyName=BallMinSize&value=N` : Ball 최소 크기(N은 숫자)
- `/teaching/bga/update?propertyName=BallMaxSize&value=N` : Ball 최대 크기(N은 숫자)
- `/teaching/bga/update?propertyName=findBallRoiAutoTeaching&value=1` : BGA ball 탭에서 Auto ROI 버튼 클릭
- `/teaching/bga/update?propertyName=findBallsTeaching&value=1` : findBalls 버튼 클릭

### BGA Surface 탭
# - `/teaching/bga/update?propertyName=SurfaceRois&value=status` : 표면 검사 ROI (status는 다음 중 하나: `add`, `delete`, `reset`)
- `/teaching/bga/update?propertyName=ScratchThreshold&value=N-N` : Scratch 임계값
- `/teaching/bga/update?propertyName=ScratchSize&value=N-N` : Scratch 최소, 최대 크기 설정
# - `/teaching/bga/update?propertyName=ScratchMaxSize&value=N` : Scratch 최대 크기
- `/teaching/bga/update?propertyName=ForeignMaterialThreshold&value=N-N` : 이물질 임계값
- `/teaching/bga/update?propertyName=ForeignMaterialSize&value=N-N` : 이물질 최소, 최대 크기 설정
# - `/teaching/bga/update?propertyName=ForeignMaterialMaxSize&value=N` : 이물질 최대 크기
- `/teaching/bga/update?propertyName=ContaminationThreshold&value=N-N` : 오염 임계값
- `/teaching/bga/update?propertyName=ContaminationSize&value=N-N` : 오염 최소, 최대 크기 설정
# - `/teaching/bga/update?propertyName=ContaminationMaxSize&value=N` : 오염 최대 크기
- `/teaching/bga/update?propertyName=inspectSurfaceTeaching&value=1` : inspectSurface 버튼 클릭


### BGA Sawing 탭
# - `/teaching/bga/update?propertyName=SawOffsetItems&value=[{"Standard":N,"Offset":N,...}]` : Saw Offset
- `/teaching/bga/update?propertyName=SawOffsetItems&value=N-N` : Saw Offset 설정
- `/teaching/bga/update?propertyName=OutlineThreshold&value=N-N` : 외곽선 임계값
- `/teaching/bga/update?propertyName=MinLengthOfShortSide&value=N` : 짧은 변 최소 길이
- `/teaching/bga/update?propertyName=MaxLengthOfShortSide&value=N` : 짧은 변 최대 길이
- `/teaching/bga/update?propertyName=MinLengthOfLongSide&value=N` : 긴 변 최소 길이
- `/teaching/bga/update?propertyName=MaxLengthOfLongSide&value=N` : 긴 변 최대 길이
- `/teaching/bga/update?propertyName=inspectSawingTeaching&value=1` : inspect Sawing 버튼 클릭
- `/teaching/bga/update?propertyName=OutlineWidth&value=N` : 외곽선 너비(N은 숫자)

### BGA Reject Mark 탭
# - `/teaching/bga/update?propertyName=RejectMarkRoi&value={"Row1":N,"Column1":N,"Row2":N,"Column2":N}` : Reject Mark ROI
# - `/teaching/bga/update?propertyName=RejectMarkRoi_&value=N-N-N-N` : Reject Mark ROI
- `/teaching/bga/update?propertyName=RejectMarkThreshold&value=N-N` : Reject Mark 임계값
- `/teaching/bga/update?propertyName=RejectMarkMinSize&value=N-N` : Reject Mark 최소, 최대 크기
# - `/teaching/bga/update?propertyName=RejectMarkMaxSize&value=N` : Reject Mark 최대 크기
- `/teaching/bga/update?propertyName=inspectRejectMarkTeaching&value=1` : inspectRejectMark 버튼 클릭

### BGA Don't Care 탭
# - `/teaching/bga/update?propertyName=DontCareRois&value=status` : Don't Care ROI, (status 는 다음 중 하나: ADD, RESET, DELETE)
# - `/teaching/bga/update?propertyName=DontCareRois_&value=N-N-N-N` : Don't Care ROI

### BGA Result 탭
- `/teaching/bga/update?propertyName=inspectTeaching&value=1` : Result 탭 Inspection 버튼 클릭

### BGA 티칭 창 ROI 생성/삭제/초기화 버튼
- `/teaching/bga/update?propertyName=PatternRois&value=status` : BGA 티칭 창 FirstPin/Pattern 탭 ROI 추가,삭제,초기화 
- `/teaching/bga/update?propertyName=BallRoi&value=status` : BGA 티칭 창 Ball 탭 ROI 추가,삭제,초기화 
- `/teaching/bga/update?propertyName=RejectMarkRoi&value=status` : BGA 티칭 창 RejectMark 탭 ROI 추가,삭제,초기화 
- `/teaching/bga/update?propertyName=DontCareRoi&value=status` : BGA 티칭 창 DontCare 탭 ROI 추가,삭제,초기화 

## calibration 창 값 변경 및 업데이트
- `/calibration/update?propertyName=button&value=status` : 보정(캘리브레이션) 창에서 특정 버튼 클릭 (status=다음 중 하나: `Test`, `LightSave`)
- `/calibration/update?propertyName=tab&value=status` : 보정(캘리브레이션) 창에서 특정 탭 클릭 (status=다음 중 하나: `bottom`, `setting`,`pad`,'tray','vision')
- `/calibration/update?propertyName=roi&value=status` : 보정(캘리브레이션) 창에서 로이 생성 혹은 초기화(재생성) (status =다음 중 하나: `create`, `recreate`)
- `/calibration/update?propertyName=threshold&value=minN-maxN` : 보정(캘리브레이션) 창에서 임계값 설정 (예시: 임계값 100-200 /calibration/parameter?threshold=100-200, 임계값 초기화 /calibration/parameter?threshold=0-255)
- `/calibration/update?propertyName=size&value=minN-maxN` : 보정(캘리브레이션) 창에서 사이즈 설정
- `/calibration/update?propertyName=shape&value=status-N` : 보정(캘리브레이션) 창에서 유사도 설정 (status는 다음 중 하나: `rectangle`, `circle`)(N은 Similarity 숫자)(예시: 모양 원, 60 /calibration/update?propertyName=shape&value=circle-60)
- `/calibration/update?propertyName=select&value=status` : 보정(캘리브레이션) 창에서 기준 설정 (status는 다음 중 하나: `MULTIOBJECT`, `CENTER`, `BIGGEST`)
- `/calibration/update?propertyName=RETICLETYPE&value=status` : 보정(캘리브레이션) 창에서 십자선 타입 설정 (status는 다음 중 하나: `NONE`, `DEFAULT`, `FULLSIZE`)
- `/calibration/update?propertyName=camera&value=status` : 보정(캘리브레이션) 창에서 카메라 변경 (status는 다음 중 하나: `)

`/execute/yes`
`/execute/no`

- `/history/update?propertyName=date&value=YYYY-MM-DD_YYYY-MM-DD` : 특정 날짜의 검사 기록. 단, YYYY-MM-DD 대신 실제 날짜를 넣어야 해. 
- `/history/update?propertyName=camera&value=status` : 기록 창에서 카메라 필터 설정. (status=다음 중 하나: `NotSelected`, `Mapping`, `SettingX1`, `SettingX2`, `PRS`, `BarCode`, `TopBarCode`, `Side` )
- `/history/update?propertyName=inspection&value=status` : 기록 창에서 검사 필터 설정. (status=다음 중 하나: `NotSelected`, `Mapping`, `Mark`, `Qfn`, `Bga`, `Lga`, `DataCode`, `BottomDataCode` , `Strip` )
- `/history/update?propertyName=BUTTON&value=status` : 기록 창에서 검사 필터 설정. (status=다음 중 하나: `save`, `open`)

### LGA 티칭 창 임계값 변경
-`/teaching/lga/update?propertyName=PackageThreshold&value=N-N` : LGA 티칭 창 package 탭에서 임계값 설정(N 은 숫자)
-`/teaching/lga/update?propertyName=FirstPinThreshold&value=N-N` : LGA 티칭 창 package FirstPin 임계값 설정(N 은 숫자)
-`/teaching/lga/update?propertyName=MultiPadThreshold&value=N-N` : LGA 티칭 창 Pad 탭에서 임계값 설정(N 은 숫자)
-`/teaching/lga/update?propertyName=LeadThreshold&value=N-N` : LGA 티칭 창 Lead 탭에서 임계값 설정(N 은 숫자)
-`/teaching/lga/update?propertyName=ScratchThreshold&value=N-N` : LGA 티칭 창 Scratch 임계값 설정(N 은 숫자)
-`/teaching/lga/update?propertyName=ForeignMaterialThreshold&value=N-N` : LGA 티칭 창 ForeignMaterial 임계값 설정(N 은 숫자)
-`/teaching/lga/update?propertyName=ContaminationThreshold&value=N-N` : LGA 티칭 창 Contamination 임계값 설정(N 은 숫자)
-`/teaching/lga/update?propertyName=OutlineThreshold&value=N-N` : LGA 티칭 창 sawing 탭에서 임계값 설정(N 은 숫자)
-`/teaching/lga/update?propertyName=RejectMarkThreshold&value=N-N` : LGA 티칭 창 RejectMark 탭에서 임계값 설정(N 은 숫자)
(예시: lga 창 package 탭에서 임계값 2-33, /teaching/lga/update?propertyName=PackageThreshold&value=2-33)

### LGA 티칭 창 사이즈값 변경
-`/teaching/lga/update?propertyName=PadContaminationSize&value=N-N` : LGA 티칭 창 Pad 탭 사이즈 설정(N 은 숫자)
-`/teaching/lga/update?propertyName=LeadContaminationSize&value=N-N` : LGA 티칭 창 Lead 탭 사이즈 설정(N 은 숫자)
-`/teaching/lga/update?propertyName=ScratchSize&value=N-N` : LGA 티칭 창 Scratch 탭 사이즈 설정(N 은 숫자)
-`/teaching/lga/update?propertyName=ForeignMaterialSize&value=N-N` : LGA 티칭 창 ForeignMaterial 사이즈 설정(N 은 숫자)
-`/teaching/lga/update?propertyName=ContaminationSize&value=N-N` : LGA 티칭 창 Contamination 사이즈 설정(N 은 숫자)
-`/teaching/lga/update?propertyName=RejectMarkSize&value=N-N` : LGA 티칭 창 RejectMark 탭 사이즈 설정(N 은 숫자)

### LGA 티칭 창 ROI 생성/삭제/초기화 버튼
- `/teaching/lga/update?propertyName=PadRois&value=status` : LGA 티칭 창 Pad 탭 ROI 추가,삭제,초기화 
- `/teaching/lga/update?propertyName=SurfaceRoi&value=status` : LGA 티칭 창 Surface 탭 ROI 추가,삭제,초기화 
- `/teaching/lga/update?propertyName=DontCareRoi&value=status` : LGA 티칭 창 DontCare 탭 ROI 추가,삭제,초기화 
- `/teaching/lga/update?propertyName=LeadRois&value=status` : LGA 티칭 창 Lead 탭 ROI 추가,삭제,초기화 
(status는 다음 중 하나: `add`, `delete`, `reset`)
,(예시: lga 창 surface 탭 roi add, /teaching/lga/update?propertyName=SurfaceRois&value=add)

### LGA 티칭 창 roi, threshold 자동 생성 버튼
- `/teaching/lga/update?propertyName=findPackageRoiAutoCommand&value=1` : LGA 티칭 창에서 ROI 자동 생성
- `/teaching/lga/update?propertyName=autoThresholdCommand&value=1` : LGA 티칭 창에서 임계값 자동 설정

### LGA 티칭 테스트
- `/teaching/lga/update?propertyName=FindPackagesTeaching&value=1` : LGA 티칭 창에서 티칭 테스트 버튼 클릭
- `/teaching/lga/update?propertyName=findpadsTeaching&value=1` : LGA 티칭 창에서 티칭 테스트 버튼 클릭
- `/teaching/lga/update?propertyName=findLeadsTeaching&value=1` : LGA 티칭 창에서 티칭 테스트 버튼 클릭
- `/teaching/lga/update?propertyName=findSurfaceTeaching&value=1` : LGA 티칭 창에서 티칭 테스트 버튼 클릭
- `/teaching/lga/update?propertyName=findSawingTeaching&value=1` : LGA 티칭 창에서 티칭 테스트 버튼 클릭
- `/teaching/lga/update?propertyName=inspectRejectMarkTeaching&value=1` : LGA 티칭 창에서 티칭 테스트 버튼 클릭 
- `/teaching/lga/update?propertyName=inspectTeaching&value=1` : LGA 티칭 창에서 티칭 테스트 버튼 클릭 

### LGA combobox 값 변경
- `/teaching/lga/update?propertyName=PackageEdgeDetectDirection&value=status` : LGA 티칭 창 edge 방향값 변경(status는 다음 중 하나: `InToOut`, `OutToIn`)
- `/teaching/lga/update?propertyName=PackageEdgeDetectMode&value=status` : LGA 티칭 창 edge 모드 변경 (status는 다음 중 하나: `BlackToWhite`, `WhiteToBlack`)

### LGA 티칭 창 탭 이동
- `/teaching/lga/update?propertyName=moveTab&value=status` : LGA 티칭 창에서 특정 탭으로 이동 (status는 다음 중 하나: `Package`, `Pads`, `Leads`, `Surface`, `Sawing`, `RejectMark`, `DontCare`, `Result`)

### LGA 티칭 창 roi 단일 생성 버튼
- `/teaching/lga/update?propertyName=PackageRoiTop_&value=N-N-N-N` : LGA 티칭 창 해당 탭에서 ROI 생성
- `/teaching/lga/update?propertyName=PackageRoiLeft_&value=N-N-N-N` : LGA 티칭 창 해당 탭에서 ROI 생성
- `/teaching/lga/update?propertyName=PackageRoiBottom_&value=N-N-N-N` : LGA 티칭 창 해당 탭에서 ROI 생성
- `/teaching/lga/update?propertyName=PackageRoiRight_&value=N-N-N-N` : LGA 티칭 창 해당 탭에서 ROI 생성
- `/teaching/lga/update?propertyName=PackageModelRoi_&value=N-N-N-N` : LGA 티칭 창 해당 탭에서 ROI 생성
- `/teaching/lga/update?propertyName=FirstPinRoi_&value=N-N-N-N` : LGA 티칭 창 해당 탭에서 ROI 생성
- `/teaching/lga/update?propertyName=RejectMarkRoi_&value=N-N-N-N` : LGA 티칭 창 RejectMark 탭에서 ROI 생성
(예시: lga 창 model roi 10-20-30-40, /teaching/lga/update?propertyName=PackageModelRoi_&value=10-20-30-40)
(예시2: lga 창 Package Roi Top 생성, /teaching/lga/update?propertyName=PackageModelRoi_&value=1)

### lga 값 변경
- `/teaching/lga/update?propertyName=OutlineWidth&value=N` : 외곽선 너비(N은 숫자)
- `/teaching/lga/update?propertyName=PackageThresholdDiff&value=N` : Edge Threshold Amplitude 값 설정(N은 숫자)
- `/teaching/lga/update?propertyName=FirstPinType&value=status` : LGA 티칭 창에서 첫 번째 핀 타입 속성 업데이트(status는 다음 중 하나:  `SmallPad`, `Notch`, `Chamfer`)

- `/windows/light/live?camera=PRS` : PRS 카메라 실시간 라이브 뷰 열기
- `/windows/light/live?camera=BarCode` : BarCode 카메라 실시간 라이브 뷰 열기
- `/windows/light/live?camera=SettingX1` : SettingX1 카메라 실시간 라이브 뷰 열기
- `/windows/light/live?camera=SettingX2` : SettingX2 카메라 실시간 라이브 뷰 열기
- `/windows/light/live?camera=Mapping` : Mapping 카메라 실시간 라이브 뷰 열기

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

### Setting Recipe:
- `/settings/update?propertyName=TrayRowCount&value=값` : TrayRowCount 값을 변경 (예: 8)
- `/settings/update?propertyName=TrayColCount&value=값` : TrayColCount 값을 변경 (예: 10)
- `/settings/update?propertyName=FovRowCount&value=값` : FovRowCount 값을 변경 (예: 5)
- `/settings/update?propertyName=FovColCount&value=값` : FovColCount 값을 변경 (예: 4)
- `/settings/update?propertyName=BlockRowCount&value=값` : BlockRowCount 값을 변경 (예: 6)
- `/settings/update?propertyName=BlockColCount&value=값` : BlockColCount 값을 변경 (예: 7)
- `/settings/update?propertyName=PackageHeight&value=값` : PackageHeight 값을 변경 (예: 12.3)
- `/settings/update?propertyName=PackageWidth&value=값` : PackageWidth 값을 변경 (예: 10.5)
- `/settings/update?propertyName=PrsPackageType&value=값` : PrsPackageType 값을 변경 (예: QFN)
- `/settings/update?propertyName=MapPackageType&value=값` : MapPackageType 값을 변경 (예: BGA)
- `/settings/update?propertyName=IsMappingUsed&value=값` : IsMappingUsed 값을 변경 (예: true)
- `/settings/update?propertyName=IsPrsUsed&value=값` : IsPrsUsed 값을 변경 (예: false)
- `/settings/update?propertyName=IsBarcodeUsed&value=값` : IsBarcodeUsed 값을 변경 (예: true)
### Setting BGA inspection:
- `/settings/update?propertyName=UseBgaNoDevice&value=값` : UseBgaNoDevice 값을 변경 (예: true)
- `/settings/update?propertyName=BgaNoDeviceColor&value=값` : BgaNoDeviceColor 값을 변경 (예: Red)
- `/settings/update?propertyName=UseBgaPackageSize&value=값` : UseBgaPackageSize 값을 변경 (예: false)
- `/settings/update?propertyName=BgaPackageSizeColor&value=값` : BgaPackageSizeColor 값을 변경 (예: Green)
- `/settings/update?propertyName=UseBgaPackageOffset&value=값` : UseBgaPackageOffset 값을 변경 (예: true)
- `/settings/update?propertyName=BgaPackageOffsetColor&value=값` : BgaPackageOffsetColor 값을 변경 (예: Blue)
- `/settings/update?propertyName=UseBgaCornerDegree&value=값` : UseBgaCornerDegree 값을 변경 (예: true)
- `/settings/update?propertyName=BgaCornerDegreeColor&value=값` : BgaCornerDegreeColor 값을 변경 (예: Yellow)
- `/settings/update?propertyName=UseBgaFirstPin&value=값` : UseBgaFirstPin 값을 변경 (예: false)
- `/settings/update?propertyName=BgaFirstPinColor&value=값` : BgaFirstPinColor 값을 변경 (예: Cyan)
- `/settings/update?propertyName=UseBgaPattern&value=값` : UseBgaPattern 값을 변경 (예: true)
- `/settings/update?propertyName=BgaPatternColor&value=값` : BgaPatternColor 값을 변경 (예: Magenta)
- `/settings/update?propertyName=UseBgaBallCount&value=값` : UseBgaBallCount 값을 변경 (예: true)
- `/settings/update?propertyName=BgaBallCountColor&value=값` : BgaBallCountColor 값을 변경 (예: Orange)
- `/settings/update?propertyName=UseBgaBallSize&value=값` : UseBgaBallSize 값을 변경 (예: false)
- `/settings/update?propertyName=BgaBallSizeColor&value=값` : BgaBallSizeColor 값을 변경 (예: Purple)
- `/settings/update?propertyName=UseBgaBallPitch&value=값` : UseBgaBallPitch 값을 변경 (예: true)
- `/settings/update?propertyName=BgaBallPitchColor&value=값` : BgaBallPitchColor 값을 변경 (예: Black)
- `/settings/update?propertyName=UseBgaBallBridging&value=값` : UseBgaBallBridging 값을 변경 (예: false)
- `/settings/update?propertyName=BgaBallBridgingColor&value=값` : BgaBallBridgingColor 값을 변경 (예: White)
- `/settings/update?propertyName=UseBgaExtraBall&value=값` : UseBgaExtraBall 값을 변경 (예: true)
- `/settings/update?propertyName=BgaExtraBallColor&value=값` : BgaExtraBallColor 값을 변경 (예: Gray)
- `/settings/update?propertyName=UseBgaMissingBall&value=값` : UseBgaMissingBall 값을 변경 (예: false)
- `/settings/update?propertyName=BgaMissingBallColor&value=값` : BgaMissingBallColor 값을 변경 (예: Brown)
- `/settings/update?propertyName=UseBgaCrackBall&value=값` : UseBgaCrackBall 값을 변경 (예: true)
- `/settings/update?propertyName=BgaCrackBallColor&value=값` : BgaCrackBallColor 값을 변경 (예: Pink)
- `/settings/update?propertyName=UseBgaScratch&value=값` : UseBgaScratch 값을 변경 (예: false)
- `/settings/update?propertyName=BgaScratchColor&value=값` : BgaScratchColor 값을 변경 (예: Teal)
- `/settings/update?propertyName=UseBgaForeignMaterial&value=값` : UseBgaForeignMaterial 값을 변경 (예: true)
- `/settings/update?propertyName=BgaForeignMaterialColor&value=값` : BgaForeignMaterialColor 값을 변경 (예: Navy)
- `/settings/update?propertyName=UseBgaContamination&value=값` : UseBgaContamination 값을 변경 (예: false)
- `/settings/update?propertyName=BgaContaminationColor&value=값` : BgaContaminationColor 값을 변경 (예: Lime)
- `/settings/update?propertyName=UseBallPosition&value=값` : UseBallPosition 값을 변경 (예: true)
- `/settings/update?propertyName=BgaBallPositionColor&value=값` : BgaBallPositionColor 값을 변경 (예: Olive)
- `/settings/update?propertyName=UseBgaSawOffset&value=값` : UseBgaSawOffset 값을 변경 (예: false)
- `/settings/update?propertyName=BgaSawOffsetColor&value=값` : BgaSawOffsetColor 값을 변경 (예: Maroon)
- `/settings/update?propertyName=UseBgaChipping&value=값` : UseBgaChipping 값을 변경 (예: true)
- `/settings/update?propertyName=BgaChippingColor&value=값` : BgaChippingColor 값을 변경 (예: Aqua)
- `/settings/update?propertyName=UseBgaBurr&value=값` : UseBgaBurr 값을 변경 (예: false)
- `/settings/update?propertyName=BgaBurrColor&value=값` : BgaBurrColor 값을 변경 (예: Silver)
- `/settings/update?propertyName=UseBgaRejectMark&value=값` : UseBgaRejectMark 값을 변경 (예: true)
- `/settings/update?propertyName=BgaRejectMarkColor&value=값` : BgaRejectMarkColor 값을 변경 (예: Gold)
- `/settings/update?propertyName=BgaXOutColor&value=값` : BgaXOutColor 값을 변경 (예: Crimson)
- `/settings/update?propertyName=BgaXOut2Color&value=값` : BgaXOut2Color 값을 변경 (예: Indigo)
### Setting QFNInspection:
- `/settings/update?propertyName=UseQfnNoDevice&value=값` : UseQfnNoDevice 값을 변경 (예: true)
- `/settings/update?propertyName=QfnNoDeviceColor&value=값` : QfnNoDeviceColor 값을 변경 (예: Red)
- `/settings/update?propertyName=UseQfnPackageSize&value=값` : UseQfnPackageSize 값을 변경 (예: false)
- `/settings/update?propertyName=QfnPackageSizeColor&value=값` : QfnPackageSizeColor 값을 변경 (예: Green)
- `/settings/update?propertyName=UseQfnPackageOffset&value=값` : UseQfnPackageOffset 값을 변경 (예: true)
- `/settings/update?propertyName=QfnPackageOffsetColor&value=값` : QfnPackageOffsetColor 값을 변경 (예: Blue)
- `/settings/update?propertyName=UseQfnCornerDegree&value=값` : UseQfnCornerDegree 값을 변경 (예: true)
- `/settings/update?propertyName=QfnCornerDegreeColor&value=값` : QfnCornerDegreeColor 값을 변경 (예: Yellow)
- `/settings/update?propertyName=UseQfnFirstPin&value=값` : UseQfnFirstPin 값을 변경 (예: false)
- `/settings/update?propertyName=QfnFirstPinColor&value=값` : QfnFirstPinColor 값을 변경 (예: Cyan)
- `/settings/update?propertyName=UseQfnPadSize&value=값` : UseQfnPadSize 값을 변경 (예: true)
- `/settings/update?propertyName=QfnPadSizeColor&value=값` : QfnPadSizeColor 값을 변경 (예: Magenta)
- `/settings/update?propertyName=UseQfnPadArea&value=값` : UseQfnPadArea 값을 변경 (예: false)
- `/settings/update?propertyName=QfnPadAreaColor&value=값` : QfnPadAreaColor 값을 변경 (예: Orange)
- `/settings/update?propertyName=UseQfnLeadCount&value=값` : UseQfnLeadCount 값을 변경 (예: true)
- `/settings/update?propertyName=QfnLeadCountColor&value=값` : QfnLeadCountColor 값을 변경 (예: Purple)
- `/settings/update?propertyName=UseQfnLeadSize&value=값` : UseQfnLeadSize 값을 변경 (예: false)
- `/settings/update?propertyName=QfnLeadSizeColor&value=값` : QfnLeadSizeColor 값을 변경 (예: Black)
- `/settings/update?propertyName=UseQfnLeadPitch&value=값` : UseQfnLeadPitch 값을 변경 (예: true)
- `/settings/update?propertyName=QfnLeadPitchColor&value=값` : QfnLeadPitchColor 값을 변경 (예: White)
- `/settings/update?propertyName=UseQfnLeadOffset&value=값` : UseQfnLeadOffset 값을 변경 (예: false)
- `/settings/update?propertyName=QfnLeadOffsetColor&value=값` : QfnLeadOffsetColor 값을 변경 (예: Gray)
- `/settings/update?propertyName=UseQfnLeadArea&value=값` : UseQfnLeadArea 값을 변경 (예: true)
- `/settings/update?propertyName=QfnLeadAreaColor&value=값` : QfnLeadAreaColor 값을 변경 (예: Brown)
- `/settings/update?propertyName=UseQfnLeadContamination&value=값` : UseQfnLeadContamination 값을 변경 (예: false)
- `/settings/update?propertyName=QfnLeadContaminationColor&value=값` : QfnLeadContaminationColor 값을 변경 (예: Pink)
- `/settings/update?propertyName=UseQfnLeadPerimeter&value=값` : UseQfnLeadPerimeter 값을 변경 (예: true)
- `/settings/update?propertyName=QfnLeadPerimeterColor&value=값` : QfnLeadPerimeterColor 값을 변경 (예: Teal)
- `/settings/update?propertyName=UseQfnScratch&value=값` : UseQfnScratch 값을 변경 (예: false)
- `/settings/update?propertyName=QfnScratchColor&value=값` : QfnScratchColor 값을 변경 (예: Navy)
- `/settings/update?propertyName=UseQfnForeignMaterial&value=값` : UseQfnForeignMaterial 값을 변경 (예: true)
- `/settings/update?propertyName=QfnForeignMaterialColor&value=값` : QfnForeignMaterialColor 값을 변경 (예: Lime)
- `/settings/update?propertyName=UseQfnContamination&value=값` : UseQfnContamination 값을 변경 (예: false)
- `/settings/update?propertyName=QfnContaminationColor&value=값` : QfnContaminationColor 값을 변경 (예: Olive)
- `/settings/update?propertyName=UseQfnSawOffset&value=값` : UseQfnSawOffset 값을 변경 (예: true)
- `/settings/update?propertyName=QfnSawOffsetColor&value=값` : QfnSawOffsetColor 값을 변경 (예: Maroon)
- `/settings/update?propertyName=UseQfnChipping&value=값` : UseQfnChipping 값을 변경 (예: false)
- `/settings/update?propertyName=QfnChippingColor&value=값` : QfnChippingColor 값을 변경 (예: Aqua)
- `/settings/update?propertyName=UseQfnBurr&value=값` : UseQfnBurr 값을 변경 (예: true)
- `/settings/update?propertyName=QfnBurrColor&value=값` : QfnBurrColor 값을 변경 (예: Silver)
- `/settings/update?propertyName=UseQfnRejectMark&value=값` : UseQfnRejectMark 값을 변경 (예: false)
- `/settings/update?propertyName=QfnRejectMarkColor&value=값` : QfnRejectMarkColor 값을 변경 (예: Gold)
- `/settings/update?propertyName=QfnXOutColor&value=값` : QfnXOutColor 값을 변경 (예: Crimson)
### Setting MAPInspection:
- `/settings/update?propertyName=UseMapNoDevice&value=값` : UseMapNoDevice 값을 변경 (예: true)
- `/settings/update?propertyName=MapNoDeviceColor&value=값` : MapNoDeviceColor 값을 변경 (예: Red)
- `/settings/update?propertyName=UseMapPackageSize&value=값` : UseMapPackageSize 값을 변경 (예: false)
- `/settings/update?propertyName=MapPackageSizeColor&value=값` : MapPackageSizeColor 값을 변경 (예: Green)
- `/settings/update?propertyName=UseMapPackageOffset&value=값` : UseMapPackageOffset 값을 변경 (예: true)
- `/settings/update?propertyName=MapPackageOffsetColor&value=값` : MapPackageOffsetColor 값을 변경 (예: Blue)
- `/settings/update?propertyName=UseMapCornerDegree&value=값` : UseMapCornerDegree 값을 변경 (예: true)
- `/settings/update?propertyName=MapCornerDegreeColor&value=값` : MapCornerDegreeColor 값을 변경 (예: Yellow)
- `/settings/update?propertyName=UseMapNoMark&value=값` : UseMapNoMark 값을 변경 (예: false)
- `/settings/update?propertyName=MapNoMarkColor&value=값` : MapNoMarkColor 값을 변경 (예: Cyan)
- `/settings/update?propertyName=UseMapMarkCount&value=값` : UseMapMarkCount 값을 변경 (예: true)
- `/settings/update?propertyName=MapMarkCountColor&value=값` : MapMarkCountColor 값을 변경 (예: Magenta)
- `/settings/update?propertyName=UseMapWrongMark&value=값` : UseMapWrongMark 값을 변경 (예: false)
- `/settings/update?propertyName=MapWrongMarkColor&value=값` : MapWrongMarkColor 값을 변경 (예: Orange)
- `/settings/update?propertyName=UseMapTextAngle&value=값` : UseMapTextAngle 값을 변경 (예: true)
- `/settings/update?propertyName=MapTextAngleColor&value=값` : MapTextAngleColor 값을 변경 (예: Purple)
- `/settings/update?propertyName=UseMapTextOffset&value=값` : UseMapTextOffset 값을 변경 (예: false)
- `/settings/update?propertyName=MapTextOffsetColor&value=값` : MapTextOffsetColor 값을 변경 (예: Black)
- `/settings/update?propertyName=UseMapDataCode&value=값` : UseMapDataCode 값을 변경 (예: true)
- `/settings/update?propertyName=MapDataCodeColor&value=값` : MapDataCodeColor 값을 변경 (예: White)
- `/settings/update?propertyName=UseMapMissingChar&value=값` : UseMapMissingChar 값을 변경 (예: false)
- `/settings/update?propertyName=MapMissingCharColor&value=값` : MapMissingCharColor 값을 변경 (예: Gray)
- `/settings/update?propertyName=UseMapScratch&value=값` : UseMapScratch 값을 변경 (예: true)
- `/settings/update?propertyName=MapScratchColor&value=값` : MapScratchColor 값을 변경 (예: Brown)
- `/settings/update?propertyName=UseMapForeignMaterial&value=값` : UseMapForeignMaterial 값을 변경 (예: false)
- `/settings/update?propertyName=MapForeignMaterialColor&value=값` : MapForeignMaterialColor 값을 변경 (예: Pink)
- `/settings/update?propertyName=UseMapContamination&value=값` : UseMapContamination 값을 변경 (예: true)
- `/settings/update?propertyName=MapContaminationColor&value=값` : MapContaminationColor 값을 변경 (예: Teal)
- `/settings/update?propertyName=UseMapSawOffset&value=값` : UseMapSawOffset 값을 변경 (예: false)
- `/settings/update?propertyName=MappingSawOffsetColor&value=값` : MappingSawOffsetColor 값을 변경 (예: Navy)
- `/settings/update?propertyName=UseMapChipping&value=값` : UseMapChipping 값을 변경 (예: true)
- `/settings/update?propertyName=MapChippingColor&value=값` : MapChippingColor 값을 변경 (예: Lime)
- `/settings/update?propertyName=UseMapBurr&value=값` : UseMapBurr 값을 변경 (예: false)
- `/settings/update?propertyName=MapBurrColor&value=값` : MapBurrColor 값을 변경 (예: Olive)
- `/settings/update?propertyName=UseMapRejectMark&value=값` : UseMapRejectMark 값을 변경 (예: true)
- `/settings/update?propertyName=MapRejectMarkColor&value=값` : MapRejectMarkColor 값을 변경 (예: Maroon)
- `/settings/update?propertyName=MapXOutColor&value=값` : MapXOutColor 값을 변경 (예: Aqua)
- `/settings/update?propertyName=MapXOut2Color&value=값` : MapXOut2Color 값을 변경 (예: Silver)
### Setting LGAInspection:
- `/settings/update?propertyName=UseLgaNoDevice&value=값` : UseLgaNoDevice 값을 변경 (예: true)
- `/settings/update?propertyName=LgaNoDeviceColor&value=값` : LgaNoDeviceColor 값을 변경 (예: Red)
- `/settings/update?propertyName=UseLgaPackageSize&value=값` : UseLgaPackageSize 값을 변경 (예: false)
- `/settings/update?propertyName=LgaPackageSizeColor&value=값` : LgaPackageSizeColor 값을 변경 (예: Green)
- `/settings/update?propertyName=UseLgaPackageOffset&value=값` : UseLgaPackageOffset 값을 변경 (예: true)
- `/settings/update?propertyName=LgaPackageOffsetColor&value=값` : LgaPackageOffsetColor 값을 변경 (예: Blue)
- `/settings/update?propertyName=UseLgaCornerDegree&value=값` : UseLgaCornerDegree 값을 변경 (예: true)
- `/settings/update?propertyName=LgaCornerDegreeColor&value=값` : LgaCornerDegreeColor 값을 변경 (예: Yellow)
- `/settings/update?propertyName=UseLgaFirstPin&value=값` : UseLgaFirstPin 값을 변경 (예: false)
- `/settings/update?propertyName=LgaFirstPinColor&value=값` : LgaFirstPinColor 값을 변경 (예: Cyan)
- `/settings/update?propertyName=UseLgaPadCount&value=값` : UseLgaPadCount 값을 변경 (예: true)
- `/settings/update?propertyName=LgaPadCountColor&value=값` : LgaPadCountColor 값을 변경 (예: Magenta)
- `/settings/update?propertyName=UseLgaPadSize&value=값` : UseLgaPadSize 값을 변경 (예: false)
- `/settings/update?propertyName=LgaPadSizeColor&value=값` : LgaPadSizeColor 값을 변경 (예: Orange)
- `/settings/update?propertyName=UseLgaPadPitch&value=값` : UseLgaPadPitch 값을 변경 (예: true)
- `/settings/update?propertyName=LgaPadPitchColor&value=값` : LgaPadPitchColor 값을 변경 (예: Purple)
- `/settings/update?propertyName=UseLgaPadOffset&value=값` : UseLgaPadOffset 값을 변경 (예: false)
- `/settings/update?propertyName=LgaPadOffsetColor&value=값` : LgaPadOffsetColor 값을 변경 (예: Black)
- `/settings/update?propertyName=UseLgaPadArea&value=값` : UseLgaPadArea 값을 변경 (예: true)
- `/settings/update?propertyName=LgaPadAreaColor&value=값` : LgaPadAreaColor 값을 변경 (예: White)
- `/settings/update?propertyName=UseLgaPadContamination&value=값` : UseLgaPadContamination 값을 변경 (예: false)
- `/settings/update?propertyName=LgaPadContaminationColor&value=값` : LgaPadContaminationColor 값을 변경 (예: Gray)
- `/settings/update?propertyName=UseLgaPadPerimeter&value=값` : UseLgaPadPerimeter 값을 변경 (예: true)
- `/settings/update?propertyName=LgaPadPerimeterColor&value=값` : LgaPadPerimeterColor 값을 변경 (예: Brown)
- `/settings/update?propertyName=UseLgaLeadCount&value=값` : UseLgaLeadCount 값을 변경 (예: false)
- `/settings/update?propertyName=LgaLeadCountColor&value=값` : LgaLeadCountColor 값을 변경 (예: Pink)
- `/settings/update?propertyName=UseLgaLeadSize&value=값` : UseLgaLeadSize 값을 변경 (예: true)
- `/settings/update?propertyName=LgaLeadSizeColor&value=값` : LgaLeadSizeColor 값을 변경 (예: Teal)
- `/settings/update?propertyName=UseLgaLeadPitch&value=값` : UseLgaLeadPitch 값을 변경 (예: false)
- `/settings/update?propertyName=LgaLeadPitchColor&value=값` : LgaLeadPitchColor 값을 변경 (예: Navy)
- `/settings/update?propertyName=UseLgaLeadOffset&value=값` : UseLgaLeadOffset 값을 변경 (예: true)
- `/settings/update?propertyName=LgaLeadOffsetColor&value=값` : LgaLeadOffsetColor 값을 변경 (예: Lime)
- `/settings/update?propertyName=UseLgaLeadArea&value=값` : UseLgaLeadArea 값을 변경 (예: false)
- `/settings/update?propertyName=LgaLeadAreaColor&value=값` : LgaLeadAreaColor 값을 변경 (예: Olive)
- `/settings/update?propertyName=UseLgaLeadContamination&value=값` : UseLgaLeadContamination 값을 변경 (예: true)
- `/settings/update?propertyName=LgaLeadContaminationColor&value=값` : LgaLeadContaminationColor 값을 변경 (예: Maroon)
- `/settings/update?propertyName=UseLgaLeadPerimeter&value=값` : UseLgaLeadPerimeter 값을 변경 (예: false)
- `/settings/update?propertyName=LgaLeadPerimeterColor&value=값` : LgaLeadPerimeterColor 값을 변경 (예: Aqua)
- `/settings/update?propertyName=UseLgaScratch&value=값` : UseLgaScratch 값을 변경 (예: true)
- `/settings/update?propertyName=LgaScratchColor&value=값` : LgaScratchColor 값을 변경 (예: Silver)
- `/settings/update?propertyName=UseLgaForeignMaterial&value=값` : UseLgaForeignMaterial 값을 변경 (예: false)
- `/settings/update?propertyName=LgaForeignMaterialColor&value=값` : LgaForeignMaterialColor 값을 변경 (예: Gold)
- `/settings/update?propertyName=UseLgaContamination&value=값` : UseLgaContamination 값을 변경 (예: true)
- `/settings/update?propertyName=LgaContaminationColor&value=값` : LgaContaminationColor 값을 변경 (예: Crimson)
- `/settings/update?propertyName=LgaSawOffsetY&value=값` : LgaSawOffsetY 값을 변경 (예: 0.5)
- `/settings/update?propertyName=LgaSawOffsetX&value=값` : LgaSawOffsetX 값을 변경 (예: 0.3)
- `/settings/update?propertyName=UseLgaSawOffset&value=값` : UseLgaSawOffset 값을 변경 (예: false)
- `/settings/update?propertyName=LgaSawOffsetColor&value=값` : LgaSawOffsetColor 값을 변경 (예: Indigo)
- `/settings/update?propertyName=UseLgaChipping&value=값` : UseLgaChipping 값을 변경 (예: true)
- `/settings/update?propertyName=LgaChippingColor&value=값` : LgaChippingColor 값을 변경 (예: Violet)
- `/settings/update?propertyName=UseLgaBurr&value=값` : UseLgaBurr 값을 변경 (예: false)
- `/settings/update?propertyName=LgaBurrColor&value=값` : LgaBurrColor 값을 변경 (예: Salmon)
- `/settings/update?propertyName=UseLgaRejectMark&value=값` : UseLgaRejectMark 값을 변경 (예: true)
- `/settings/update?propertyName=LgaRejectMarkColor&value=값` : LgaRejectMarkColor 값을 변경 (예: Coral)
### Setting Tolerance, ETC:
- `/settings/update?propertyName=BgaPackageSizeWidth&value=값` : BgaPackageSizeWidth 값을 변경 (예: 10.0)
- `/settings/update?propertyName=BgaPackageSizeHeight&value=값` : BgaPackageSizeHeight 값을 변경 (예: 5.0)
- `/settings/update?propertyName=BgaCornerDegree&value=값` : BgaCornerDegree 값을 변경 (예: 2.5)
- `/settings/update?propertyName=BgaSawOffsetX&value=값` : BgaSawOffsetX 값을 변경 (예: 0.3)
- `/settings/update?propertyName=BgaSawOffsetY&value=값` : BgaSawOffsetY 값을 변경 (예: 0.3)
- `/settings/update?propertyName=BgaSawOffsetXStandard&value=값` : BgaSawOffsetXStandard 값을 변경 (예: 0.5)
- `/settings/update?propertyName=BgaSawOffsetYStandard&value=값` : BgaSawOffsetYStandard 값을 변경 (예: 0.5)
- `/settings/update?propertyName=BgaBallSizeDiameter&value=값` : BgaBallSizeDiameter 값을 변경 (예: 1.0)
- `/settings/update?propertyName=BgaBallSizeDiameterStandard&value=값` : BgaBallSizeDiameterStandard 값을 변경 (예: 1.2)
- `/settings/update?propertyName=BgaBallPitch&value=값` : BgaBallPitch 값을 변경 (예: 0.8)
- `/settings/update?propertyName=BgaBallPitchStandard&value=값` : BgaBallPitchStandard 값을 변경 (예: 0.9)
- `/settings/update?propertyName=QfnPackageSizeWidth&value=값` : QfnPackageSizeWidth 값을 변경 (예: 10.0)
- `/settings/update?propertyName=QfnPackageSizeHeight&value=값` : QfnPackageSizeHeight 값을 변경 (예: 5.0)
- `/settings/update?propertyName=QfnCornerDegree&value=값` : QfnCornerDegree 값을 변경 (예: 2.0)
- `/settings/update?propertyName=QfnSawOffsetY&value=값` : QfnSawOffsetY 값을 변경 (예: 0.3)
- `/settings/update?propertyName=QfnSawOffsetX&value=값` : QfnSawOffsetX 값을 변경 (예: 0.3)
- `/settings/update?propertyName=QfnPadSizeWidth&value=값` : QfnPadSizeWidth 값을 변경 (예: 3.0)
- `/settings/update?propertyName=QfnPadSizeHeight&value=값` : QfnPadSizeHeight 값을 변경 (예: 2.0)
- `/settings/update?propertyName=QfnPadArea&value=값` : QfnPadArea 값을 변경 (예: 4)
- `/settings/update?propertyName=QfnLeadSizeWidth&value=값` : QfnLeadSizeWidth 값을 변경 (예: 1.0)
- `/settings/update?propertyName=QfnLeadSizeHeight&value=값` : QfnLeadSizeHeight 값을 변경 (예: 1.0)
- `/settings/update?propertyName=QfnLeadArea&value=값` : QfnLeadArea 값을 변경 (예: 2)
- `/settings/update?propertyName=QfnLeadPitch&value=값` : QfnLeadPitch 값을 변경 (예: 0.5)
- `/settings/update?propertyName=QfnLeadOffsetX&value=값` : QfnLeadOffsetX 값을 변경 (예: 0.1)
- `/settings/update?propertyName=QfnLeadOffsetY&value=값` : QfnLeadOffsetY 값을 변경 (예: 0.1)
- `/settings/update?propertyName=QfnLeadOffsetT&value=값` : QfnLeadOffsetT 값을 변경 (예: 0.05)
- `/settings/update?propertyName=QfnLeadPerimeter&value=값` : QfnLeadPerimeter 값을 변경 (예: 1.5)
- `/settings/update?propertyName=MapPackageSizeWidth&value=값` : MapPackageSizeWidth 값을 변경 (예: 12.0)
- `/settings/update?propertyName=MapPackageSizeHeight&value=값` : MapPackageSizeHeight 값을 변경 (예: 6.0)
- `/settings/update?propertyName=MappingSawOffsetY&value=값` : MappingSawOffsetY 값을 변경 (예: 0.2)
- `/settings/update?propertyName=MappingSawOffsetX&value=값` : MappingSawOffsetX 값을 변경 (예: 0.2)
- `/settings/update?propertyName=MarkCount&value=값` : MarkCount 값을 변경 (예: 3)
- `/settings/update?propertyName=MapTextOffsetX&value=값` : MapTextOffsetX 값을 변경 (예: 1.0)
- `/settings/update?propertyName=MapTextOffsetY&value=값` : MapTextOffsetY 값을 변경 (예: 1.0)
- `/settings/update?propertyName=MapTextOffsetT&value=값` : MapTextOffsetT 값을 변경 (예: 0.1)
- `/settings/update?propertyName=MapCornerDegree&value=값` : MapCornerDegree 값을 변경 (예: 2.0)
- `/settings/update?propertyName=LgaPackageSizeWidth&value=값` : LgaPackageSizeWidth 값을 변경 (예: 10.0)
- `/settings/update?propertyName=LgaPackageSizeHeight&value=값` : LgaPackageSizeHeight 값을 변경 (예: 5.0)
- `/settings/update?propertyName=LgaCornerDegree&value=값` : LgaCornerDegree 값을 변경 (예: 3.0)
- `/settings/update?propertyName=LgaPadSizeWidth&value=값` : LgaPadSizeWidth 값을 변경 (예: 3.0)
- `/settings/update?propertyName=LgaPadSizeHeight&value=값` : LgaPadSizeHeight 값을 변경 (예: 2.0)
- `/settings/update?propertyName=LgaPadArea&value=값` : LgaPadArea 값을 변경 (예: 4)
- `/settings/update?propertyName=LgaPadPitch&value=값` : LgaPadPitch 값을 변경 (예: 1.0)
- `/settings/update?propertyName=LgaPadOffsetX&value=값` : LgaPadOffsetX 값을 변경 (예: 0.1)
- `/settings/update?propertyName=LgaPadOffsetY&value=값` : LgaPadOffsetY 값을 변경 (예: 0.1)
- `/settings/update?propertyName=LgaPadOffsetT&value=값` : LgaPadOffsetT 값을 변경 (예: 0.05)
- `/settings/update?propertyName=LgaPadPerimeter&value=값` : LgaPadPerimeter 값을 변경 (예: 2.0)
- `/settings/update?propertyName=LgaLeadSizeWidth&value=값` : LgaLeadSizeWidth 값을 변경 (예: 1.0)
- `/settings/update?propertyName=LgaLeadSizeHeight&value=값` : LgaLeadSizeHeight 값을 변경 (예: 1.0)
- `/settings/update?propertyName=LgaLeadArea&value=값` : LgaLeadArea 값을 변경 (예: 2)
- `/settings/update?propertyName=LgaLeadPitch&value=값` : LgaLeadPitch 값을 변경 (예: 0.5)
- `/settings/update?propertyName=LgaLeadOffsetX&value=값` : LgaLeadOffsetX 값을 변경 (예: 0.1)
- `/settings/update?propertyName=LgaLeadOffsetY&value=값` : LgaLeadOffsetY 값을 변경 (예: 0.1)
- `/settings/update?propertyName=LgaLeadOffsetT&value=값` : LgaLeadOffsetT 값을 변경 (예: 0.05)
- `/settings/update?propertyName=LgaLeadPerimeter&value=값` : LgaLeadPerimeter 값을 변경 (예: 1.5)
- `/settings/update?propertyName=SaveOption&value=값` : SaveOption 값을 변경 (예: Option1)
- `/settings/update?propertyName=SaveDays&value=값` : SaveDays 값을 변경 (예: 30)
- `/settings/update?propertyName=DBSaveDays&value=값` : DBSaveDays 값을 변경 (예: 60)
- `/settings/update?propertyName=InpectionModeSelectedItem&value=값` : InpectionModeSelectedItem 값을 변경 (예: Normal)

- `/recipes/add?name=MyNewRecipe` : 새 레시피 추가 (name은 새로 생성할 레시피의 이름)
- `/recipes/add?name=test` : test 세레시피 추가
- `/recipes/copy?source=MyNewRecipe&dest=MyCopiedRecipe` : 레시피 복사(source: 복사할 원본 레시피의 이름, dest: 새로 생성될 복사본 레시피의 이름)
- `/recipes/copy?source=TestRecipe&dest=MyCopiedRecipe` : TestRecipe를 TestRecipe_Copy로 복사
- `/recipes/rename?old=MyNewRecipe&new=MyRenamedRecipe` : 레시피 이름 변경(old: 변경할 기존 레시피의 이름, new: 새로 변경할 레시피의 이름)
- `/recipes/rename?old=TestRecipe&new=RenamedRecipe` : TestRecipe'를 'RenamedRecipe'로 변경
- `/recipes/delete?name=MyCopiedRecipe` : 레시피 삭제 (name = 삭제할 레시피의 이름)
- `/recipes/delete?name=Test` : Test 레시피 삭제
- `/recipes/select?name=MyRenamedRecipe` : 레시피 선택/적용(name = 선택하여 적용할 레시피의 이름)
- `/recipes/select?name=Test` : Test 레시피 선택

### Strip 티칭 창 roi 단일 생성 버튼
- `/teaching/strip/update?propertyName=StripRois&value=N-N-N-N` : Strip 티칭 창 해당 탭에서 ROI 생성
### Strip 티칭 창 ROI 생성/삭제/초기화 버튼
- `/teaching/Strip/update?propertyName=Roi&value=st atus` : Strip 티칭 창 Pad 탭 ROI 추가,삭제,초기화 
(status는 다음 중 하나: `add`, `delete`, `reset`)
### Strip 티칭 창 findCode 버튼 클릭
- `/teaching/strip/update?propertyName=findCodeTeaching&value=1` : Strip 티칭 창 findCode 버튼 클릭

`/NO_FUNCTION`

## 단순 창 열기
- `/windows/teaching/lga` : LGA 티칭 창 열기
- `/windows/teaching/qfn` : QFN 티칭 창 열기
- `/windows/teaching/bga` : BGA 티칭 창 열기
- `/windows/teaching/mapping` : MAPPING 티칭 창 열기
- `/windows/teaching/strip` : Strip 티칭 창 열기
- `/windows/history` : 검사 기록 창 열기
- `/windows/light` : 조명 설정 창 열기
- `/windows/calibration` : 보정(캘리브레이션) 창 열기
- `/windows/settings` : 설정창 열기
- `/windows/lot` : lot data 창 열기
- `/windows/monitor` : monitor 창 열기
- `/windows/teaching/prs/reteach` : 현재 PRS 결과 기반 재티칭 창 열기
- `/windows/teaching/mapping/reteach` : 현재 매핑 샷 기반 재티칭 창 열기
- `/mode/set?mode=RUN` : 검사 모드로 변경
- `/mode/set?mode=SETUP` : 설정 모드로 변경

## A/S 지원 창 (고객 지원)
- `/windows/as` : A/S 지원 창 열기

## 조명창 실시간 라이브 뷰 열기
- `/windows/light/live?camera=PRS` : PRS 카메라 실시간 라이브 뷰 열기
- `/windows/light/live?camera=BarCode` : BarCode 카메라 실시간 라이브 뷰 열기
- `/windows/light/live?camera=SettingX1` : SettingX1 카메라 실시간 라이브 뷰 열기
- `/windows/light/live?camera=SettingX2` : SettingX2 카메라 실시간 라이브 뷰 열기
- `/windows/light/live?camera=Mapping` : Mapping 카메라 실시간 라이브 뷰 열기

## 추가 기능
- `/live/toggle?switch=ON&no=N` : 카메라 N번 라이브 켜기 (N은 1~6)
- `/live/toggle?switch=OFF&no=N` : 카메라 N번 라이브 끄기 (N은 1~6)
- `/test/run/prs` : PRS 기반 현재 레시피 및 티칭 정보 검증을 위한 테스트 실행
- `/test/run/map` : 매핑 기반 현재 레시피 및 티칭 정보 검증을 위한 테스트 실행
- `/closeWindows` : '창 끄기' 라고 치면 실행
- `/chat/clear` : '대화 초기화' 또는 '새채팅' 라고 치면 실행
- `/openWindow/yes` : 사용자가 입력한 단답이 다음 중 하나이면 실행: "응", "네", "yes", "좋아", "예"
- `/openWindow/no` : 사용자가 입력한 단답이 다음 중 하나이면 실행: "아니", "싫어", "no"

## 재티칭(Re-teach)
- `/windows/teaching/prs/reteach` : 현재 PRS 결과 기반 재티칭 창 열기
- `/windows/teaching/mapping/reteach` : 현재 매핑 샷 기반 재티칭 창 열기

## 모드 변경
- `/mode/set?mode=RUN` : 검사 모드로 변경
- `/mode/set?mode=SETUP` : 설정 모드로 변경

## 프로그램 종료
- `/exit` : 프로그램 나가기

'''

