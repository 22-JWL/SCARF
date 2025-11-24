# evaluate/repro_evaluator.py

import json
from pathlib import Path
from typing import Dict, Any, Optional, List

import pandas as pd
from tqdm import tqdm

from model_runner_evaluate import run_model_evaluate
from .accuracy_evaluator import extract_apis_from_output


def test_repro_for_one_text(text: str, num_trials: int = 3) -> Dict[str, Any]:
    """
    한 문장에 대해 num_trials 번 실행해서
    예측 API 시퀀스가 모두 같은지 확인.
    """
    preds: List[str] = []

    for _ in range(num_trials):
        raw = run_model_evaluate(text)
        apis = extract_apis_from_output(raw)
        # 여러 개일 수도 있으니 정규화해서 문자열로 저장
        canonical = "|".join(apis)
        preds.append(canonical)

    all_same = len(set(preds)) == 1

    return {
        "text": text,
        "trials": num_trials,
        "pred_sequences": preds,
        "reproducible": bool(all_same),
    }


def evaluate_reproducibility(
    csv_path: Path,
    results_dir: Path,
    sample_n: Optional[int] = 200,
    num_trials: int = 3,
    debug_n: int = 10,
) -> Dict[str, Any]:
    """
    하나의 CSV 파일을 대상으로 재현도 평가.
    - text 컬럼 필수
    - sample_n 개수만 샘플링해서 사용 (None이면 전체)
    """

    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    df = pd.read_csv(csv_path)

    if "text" not in df.columns:
        raise ValueError(f"'text' column not found in {csv_path}")

    if sample_n is not None and len(df) > sample_n:
        df = df.sample(n=sample_n, random_state=42).reset_index(drop=True)

    total = len(df)
    num_ok = 0
    per_example = []

    print("\n=== 재현도(Reproducibility) 평가 시작 ===")
    print(f"데이터셋: {csv_path}")
    print(f"샘플 개수: {total}")
    print(f"반복 횟수: {num_trials}")

    for idx, row in tqdm(df.iterrows(), total=total):
        text = str(row["text"])
        result = test_repro_for_one_text(text, num_trials=num_trials)

        if result["reproducible"]:
            num_ok += 1

        if idx < debug_n:
            print("\n-----------------------------")
            print(f"[문장] {text}")
            print(f"[예측 시퀀스] {result['pred_sequences']}")
            print(f"[재현성] {'OK' if result['reproducible'] else 'FAIL'}")

        per_example.append(result)

    repro_rate = num_ok / total if total > 0 else 0.0

    metrics = {
        "dataset": str(csv_path),
        "num_samples": total,
        "num_trials": num_trials,
        "num_reproducible": num_ok,
        "reproducibility": repro_rate,
    }

    results_dir.mkdir(parents=True, exist_ok=True)

    with open(results_dir / "reproducibility.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "metrics": metrics,
                "examples": per_example,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("\n===== 재현도 평가 결과 =====")
    print(f"Reproducibility: {repro_rate:.4f} ({num_ok}/{total})")
    print("============================")

    return metrics
