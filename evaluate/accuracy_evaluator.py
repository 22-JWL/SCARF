# evaluate/accuracy_evaluator.py

import re
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
from tqdm import tqdm

from model_runner_evaluate import run_model_evaluate


API_PATTERN = re.compile(r"/[a-zA-Z0-9_\-\/\?=&]+")


@dataclass
class DatasetConfig:
    name: str           # 예: "single", "multi", "irrelevant", "typo"
    path: Path         # CSV 경로
    kind: str          # "single" | "multi" | "irrelevant" | "typo"
    sample_n: Optional[int] = None  # 부분 샘플링 시 사용 (None이면 전체)


def extract_apis_from_output(text: str) -> List[str]:
    """LLM 출력 문자열에서 API 주소들을 모두 추출."""
    if not text:
        return ["/NO_FUNCTION"]
    apis = API_PATTERN.findall(text)
    if not apis:
        return ["/NO_FUNCTION"]
    # 중복 제거 + 정렬
    return sorted(set(apis))


def parse_gold_labels(row: pd.Series) -> List[str]:
    """
    CSV 한 행에서 정답 API 리스트를 파싱.
    - labels 컬럼이 있으면 '|' 기준으로 여러 개 분리
    - 없으면 label 컬럼을 하나짜리 리스트로
    """
    if "labels" in row and isinstance(row["labels"], str):
        raw = row["labels"].strip()
        if not raw:
            return ["/NO_FUNCTION"]
        return [x.strip() for x in raw.split("|") if x.strip()]
    elif "label" in row and isinstance(row["label"], str):
        raw = row["label"].strip()
        if "|" in raw:
            return [x.strip() for x in raw.split("|") if x.strip()]
        return [raw] if raw else ["/NO_FUNCTION"]
    else:
        # 라벨 정보가 없으면 NO_FUNCTION 으로 취급
        return ["/NO_FUNCTION"]


def evaluate_one_dataset(cfg: DatasetConfig, results_dir: Path, debug_n: int = 10) -> Dict[str, Any]:
    """
    단일 데이터셋에 대해 정확도 평가.
    kind에 따라 해석은 약간 달라질 수 있지만,
    기본 원칙은 '예측 API 집합 == 정답 API 집합' 이면 정답.
    """
    if not cfg.path.exists():
        raise FileNotFoundError(f"Dataset not found: {cfg.path}")

    df = pd.read_csv(cfg.path)

    if "text" not in df.columns:
        raise ValueError(f"'text' column not found in {cfg.path}")

    if cfg.sample_n is not None and len(df) > cfg.sample_n:
        df = df.sample(n=cfg.sample_n, random_state=42).reset_index(drop=True)

    total = len(df)
    correct = 0
    per_example = []

    print(f"\n=== [{cfg.name}] 데이터셋 평가 시작 ===")
    print(f"파일: {cfg.path}")
    print(f"샘플 개수: {total}")

    for idx, row in tqdm(df.iterrows(), total=total):
        text = str(row["text"])
        gold = parse_gold_labels(row)

        raw = run_model_evaluate(text)
        pred_apis = extract_apis_from_output(raw)

        # 집합 비교 (순서와 중복에 영향받지 않게)
        is_correct = set(pred_apis) == set(gold)
        if is_correct:
            correct += 1

        if idx < debug_n:
            print("\n-----------------------------")
            print(f"[문장] {text}")
            print(f"[정답] {gold}")
            print(f"[LLM 출력 RAW] {raw}")
            print(f"[예측 API] {pred_apis}")
            print(f"[정답 여부] {'OK' if is_correct else 'FAIL'}")

        per_example.append(
            {
                "text": text,
                "gold": gold,
                "pred": pred_apis,
                "raw": raw,
                "correct": bool(is_correct),
            }
        )

    accuracy = correct / total if total > 0 else 0.0

    metrics = {
        "dataset": cfg.name,
        "kind": cfg.kind,
        "path": str(cfg.path),
        "num_samples": total,
        "num_correct": correct,
        "accuracy": accuracy,
    }

    # 결과 저장
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(results_dir / f"accuracy_{cfg.name}.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "metrics": metrics,
                "examples": per_example,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n[{cfg.name}] Accuracy: {accuracy:.4f}")
    return metrics


def evaluate_all_datasets(
    configs: List[DatasetConfig],
    results_dir: Path,
    debug_n: int = 10,
) -> Dict[str, Any]:
    """
    여러 데이터셋에 대해 일괄 평가하고 요약 JSON을 저장.
    """
    summary = {}
    for cfg in configs:
        metrics = evaluate_one_dataset(cfg, results_dir, debug_n=debug_n)
        summary[cfg.name] = metrics

    # 요약 결과 저장
    with open(results_dir / "accuracy_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n=== 모든 데이터셋 Accuracy 평가 완료 ===")
    for name, m in summary.items():
        print(f"- {name}: {m['accuracy']:.4f} ({m['num_correct']}/{m['num_samples']})")

    return summary
