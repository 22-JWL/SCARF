# evaluate/reproducibility_evaluator.py
"""
재현도 평가 (HTTP 버전)

 핵심 포인트
- 더 이상 model_runner 를 직접 부르지 않는다.
- 실제 챗봇 서버(app.py)의 /instruct/ 엔드포인트를 그대로 호출해서
  LLM + guardrail + 프롬프트 + 후처리까지 전부 동일하게 평가한다.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List

import pandas as pd
import requests
from tqdm import tqdm

#  실제 챗봇 서버 주소 (app.py)
INSTRUCT_URL = "http://localhost:5000/instruct/"

# 평가에 사용할 LLM 이름 ( EXAONE)
DEFAULT_EVAL_MODEL = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"


@dataclass
class DatasetConfig:
    name: str
    path: Path
    kind: str = "default"
    sample_n: Optional[int] = None
    runs: int = 3


# 1) 실제 /instruct API 호출
def call_instruct_api(
    text: str,
    model_name: str = DEFAULT_EVAL_MODEL,
    current_opened_window_and_tab: Optional[Dict[str, str]] = None,
) -> str:
    """
    app.py 의 /instruct/ 엔드포인트를 그대로 호출해서
    LLM 최종 output 문자열을 가져온다.
    """
    if current_opened_window_and_tab is None:
        current_opened_window_and_tab = {}

    payload = {
        "text": text,
        "model_name": model_name,
        "current_opened_window_and_tab": current_opened_window_and_tab,
    }

    try:
        resp = requests.post(INSTRUCT_URL, json=payload, timeout=120)
    except Exception as e:
        print(f"[ERROR] /instruct 호출 실패: {e}")
        return "/NO_FUNCTION"

    if resp.status_code != 200:
        print(f"[ERROR] /instruct HTTP {resp.status_code}: {resp.text}")
        return "/NO_FUNCTION"

    try:
        data = resp.json()
    except Exception as e:
        print(f"[ERROR] /instruct 응답 JSON 파싱 실패: {e}")
        return "/NO_FUNCTION"

    output = data.get("output", "")
    if not isinstance(output, str):
        output = str(output)

    return output


# 2) LLM 출력에서 API 리스트 추출
def extract_all_apis(text: str) -> List[str]:
    if not text or not isinstance(text, str):
        return ["/NO_FUNCTION"]

    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        lines.append(line)

    return lines if lines else ["/NO_FUNCTION"]


# 3) 한 문장에 대해 runs번 /instruct 호출 → 재현도 체크
def test_reproducibility(text: str, runs: int) -> tuple[bool, list[list[str]]]:
    outputs: List[List[str]] = []

    state: Dict[str, str] = {}

    for _ in range(runs):
        raw = call_instruct_api(
            text=text,
            model_name=DEFAULT_EVAL_MODEL,
            current_opened_window_and_tab=state
        )
        apis = extract_all_apis(raw)
        outputs.append(apis)

    ok = all(o == outputs[0] for o in outputs)
    return ok, outputs


# 4) 하나의 데이터셋 평가
def evaluate_one_dataset(cfg: DatasetConfig, results_dir: Path, debug_n: int = 5):
    if not cfg.path.exists():
        raise FileNotFoundError(f"Dataset not found: {cfg.path}")

    df = pd.read_csv(cfg.path, encoding="utf-8-sig")

    if cfg.sample_n is not None and len(df) > cfg.sample_n:
        df = df.sample(n=cfg.sample_n, random_state=42).reset_index(drop=True)

    total = len(df)
    success = 0
    per_example = []

    print(f"\n=== [{cfg.name}] 재현도 평가 시작 ===")
    print(f"샘플 수: {total}, runs={cfg.runs}")

    for idx, (_, row) in enumerate(tqdm(df.iterrows(), total=total)):
        text = str(row["text"])
        ok, outputs = test_reproducibility(text, cfg.runs)

        if ok:
            success += 1

        if idx < debug_n:
            print("\n-----------------------")
            print(f"[문장] {text}")
            print(f"[outputs] {outputs}")
            print(f"[재현도] {'OK' if ok else 'FAIL'}")

        per_example.append(
            {
                "text": text,
                "runs": cfg.runs,
                "outputs": outputs,
                "consistent": bool(ok),
            }
        )

    reproducibility = success / total if total > 0 else 0.0

    metrics = {
        "dataset": cfg.name,
        "runs": cfg.runs,
        "sample_n": total,
        "consistent": success,
        "reproducibility": reproducibility,
    }

    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / f"repro_{cfg.name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"metrics": metrics, "examples": per_example}, f, indent=2, ensure_ascii=False)

    print(f"[{cfg.name}] reproducibility = {reproducibility:.4f}")
    return metrics


# 5) 전체 평가
def evaluate_all_repro(configs, results_dir: Path):
    summary = {}
    total_samples = 0
    total_consistent = 0

    for cfg in configs:
        m = evaluate_one_dataset(cfg, results_dir)
        summary[cfg.name] = m
        total_samples += m["sample_n"]
        total_consistent += m["consistent"]

    overall = (total_consistent / total_samples) if total_samples > 0 else 0.0
    summary["overall_reproducibility"] = overall

    print("\n=== 재현도 전체 요약 ===")
    for name, m in summary.items():
        if name == "overall_reproducibility":
            continue
        print(f"- {name}: {m['reproducibility']:.4f}")

    print(f"\n 전체 통합 재현도: {overall:.4f}")
    return summary
