# evaluate/evaluate_repro.py

from pathlib import Path
from .reproducibility_evaluator import (
    DatasetConfig,
    evaluate_all_repro,
)


def main(sample_n: int = 1):   # 필요하면 샘플 수 조정
    print("evaluate_repro 실행됨")

    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "datasets"
    results_dir = base_dir / "results" / "repro"

    configs = [
        DatasetConfig(
            name="single",
            path=data_dir / "single.csv",
            kind="single",
            sample_n=sample_n,
            runs=3,
        ),
        DatasetConfig(
            name="multi",
            path=data_dir / "multi.csv",
            kind="multi",
            sample_n=sample_n,
            runs=3,
        ),
        DatasetConfig(
            name="irrelevant",
            path=data_dir / "irrelevant.csv",
            kind="irrelevant",
            sample_n=sample_n,
            runs=3,
        ),
        DatasetConfig(
            name="typo",
            path=data_dir / "typo.csv",
            kind="typo",
            sample_n=sample_n,
            runs=3,
        ),
    ]

    summary = evaluate_all_repro(
        configs=configs,
        results_dir=results_dir,
    )

    print("\n=== Reproducibility Summary ===")
    for name, m in summary.items():
        if name == "overall_reproducibility":
            continue
        print(f"- {name}: {m['reproducibility']:.4f}")

    overall = summary.get("overall_reproducibility", None)
    if overall is not None:
        print(f"\n 전체 통합 재현도: {overall:.4f}")


if __name__ == "__main__":
    main()
