# evaluate/evaluate_repro_http.py
#   app.py 의 /instruct API 를 그대로 호출하는 재현도 평가기
#   prompt mismatch / guardrail mismatch / parsing mismatch 없이
#   실제 챗봇과 100% 동일한 출력 흐름으로 평가된다.

import requests
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import pandas as pd
from tqdm import tqdm


# ★ /instruct 를 그대로 호출하는 함수
def call_instruct_api(text: str):
    url = "http://localhost:5000/instruct/"
    payload = {
        "text": text,
        "model_name": "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct",
        "current_opened_window_and_tab": {}   # 평가에서는 상태 없음
    }

    try:
        r = requests.post(url, json=payload, timeout=60)
    except Exception as err:
        print(f"[ERROR] HTTP 요청 실패: {err}")
        return "/NO_FUNCTION"

    if r.status_code != 200:
        print(f"[ERROR] /instruct HTTP {r.status_code}: {r.text}")
        return "/NO_FUNCTION"

    data = r.json()
    output = data.get("output", "")

    # app.py와 완벽히 동일하게 split하기 위한 원본 반환
    return output


# 데이터셋 config
@dataclass
class DatasetConfig:
    name: str
    path: Path
    sample_n: Optional[int] = None
    runs: int = 3


# API 추출 (app.py가 반환하는 output 그대로 split)
def extract_api_list_from_output(raw_output: str):
    """app.py 출력 그대로 → 줄바꿈 기반으로 API 리스트 추출"""
    if not isinstance(raw_output, str):
        return ["/NO_FUNCTION"]

    lines = raw_output.strip().split("\n")
    apis = [line.strip() for line in lines if line.strip()]
    return apis if apis else ["/NO_FUNCTION"]


# 한 문장에 대해 runs 회 평가
def test_repro(text: str, runs: int):
    outputs = []

    for _ in range(runs):
        raw = call_instruct_api(text)
        apis = extract_api_list_from_output(raw)
        outputs.append(apis)

    ok = all(o == outputs[0] for o in outputs)
    return ok, outputs


# 하나의 데이터셋 평가
def evaluate_one_dataset(cfg: DatasetConfig, results_dir: Path, debug_n: int = 5):
    if not cfg.path.exists():
        raise FileNotFoundError(f"Dataset not found: {cfg.path}")

    df = pd.read_csv(cfg.path, encoding="utf-8-sig")

    if cfg.sample_n is not None and len(df) > cfg.sample_n:
        df = df.sample(n=cfg.sample_n, random_state=42).reset_index(drop=True)

    total = len(df)
    success = 0

    print(f"\n=== [{cfg.name}] 재현도 평가 시작 ===")
    print(f"샘플 수: {total}, runs={cfg.runs}")

    for idx, row in tqdm(df.iterrows(), total=total):
        text = str(row["text"])
        ok, outputs = test_repro(text, cfg.runs)

        if ok:
            success += 1

        # debug 출력
        if idx < debug_n:
            print("\n-----------------------")
            print(f"[문장] {text}")
            print(f"[outputs] {outputs}")
            print(f"[재현도] {'OK' if ok else 'FAIL'}")

    reproducibility = success / total if total > 0 else 0.0

    print(f"[{cfg.name}] reproducibility = {reproducibility:.4f}")
    return {"dataset": cfg.name, "reproducibility": reproducibility}


# 전체 실행
def main(sample_n: int = 100):
    print("evaluate_repro_http 실행됨")

    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "datasets"

    configs = [
        DatasetConfig(name="single", path=data_dir / "single.csv", sample_n=sample_n, runs=3),
        DatasetConfig(name="multi", path=data_dir / "multi.csv", sample_n=sample_n, runs=3),
        DatasetConfig(name="irrelevant", path=data_dir / "irrelevant.csv", sample_n=sample_n, runs=3),
        DatasetConfig(name="typo", path=data_dir / "typo.csv", sample_n=sample_n, runs=3),
    ]

    print("\n=== Reproducibility Summary ===")
    for cfg in configs:
        result = evaluate_one_dataset(cfg, base_dir / "results_http")
        print(f"- {cfg.name}: {result['reproducibility']:.4f}")


if __name__ == "__main__":
    main()
