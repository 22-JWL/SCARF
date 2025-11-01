import pandas as pd

def join_commands(cmd_col):
    # 리스트라면 콤마로 연결
    if isinstance(cmd_col, list):
        return ','.join(cmd_col)
    # 문자열이면 줄바꿈 기준 분리해서 콤마로 연결
    elif isinstance(cmd_col, str):
        return ','.join([line.strip() for line in cmd_col.splitlines() if line.strip()])
    else:
        return ''

# 각 파일을 읽어서 category/난이도 값 지정
single = pd.read_csv("./data/single.csv", encoding="cp949")
composite = pd.read_csv("./data/composite.csv", encoding="cp949")
irrelevant = pd.read_csv("./data/irrelevant.csv", encoding="cp949")
typo = pd.read_csv("./data/typo.csv", encoding="cp949")


single["category"] = "single"
single["difficulty"] = "easy"

composite["category"] = "composite"
composite["difficulty"] = "hard"

irrelevant["category"] = "irrelevant"
irrelevant["difficulty"] = "hard"

typo["category"] = "typo"
typo["difficulty"] = "medium"

# commands 컬럼 줄바꿈/리스트 값 콤마로 평탄화 (각 파일별로 처리)
for df in [single, composite, irrelevant, typo]:
    if "commands" in df.columns:
        df["commands"] = df["commands"].fillna('').apply(join_commands)

# 파일 모두 합치기
all_commands = pd.concat([single, composite, irrelevant, typo], ignore_index=True)
all_commands.to_csv("all_commands.csv", index=False)