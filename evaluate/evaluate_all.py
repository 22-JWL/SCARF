# # evaluate/evaluate_all.py ->(api_flask) python -m evaluate.evaluate_all로 실행 

# from pathlib import Path

# from .accuracy_evaluator import (
#     DatasetConfig,
#     evaluate_all_datasets,
# )
# from .repro_evaluator import evaluate_reproducibility


# def main():
#     root = Path(__file__).resolve().parent
#     dataset_dir = root / "datasets"
#     results_dir = root / "results"

#     # 1) 정확도 평가용 데이터셋 설정
#     configs = [
#         DatasetConfig(
#             name="single",
#             path=dataset_dir / "single.csv",
#             kind="single",
#             sample_n=None,   # 전체 사용 (원하면 숫자로 줄이면 됨)
#         ),
#         DatasetConfig(
#             name="multi",
#             path=dataset_dir / "multi.csv",
#             kind="multi",
#             sample_n=None,
#         ),
#         DatasetConfig(
#             name="irrelevant",
#             path=dataset_dir / "irrelevant.csv",
#             kind="irrelevant",
#             sample_n=None,
#         ),
#         DatasetConfig(
#             name="typo",
#             path=dataset_dir / "typo.csv",
#             kind="typo",
#             sample_n=None,
#         ),
#     ]

#     # 2) 정확도 평가
#     accuracy_summary = evaluate_all_datasets(
#         configs=configs,
#         results_dir=results_dir,
#         debug_n=5,   # 각 데이터셋에서 처음 5개만 디버그 출력
#     )

#     # 3) 재현도 평가
#     #    재현도는 보통 "전체 명령 데이터셋" 하나에 대해 수행.
#     #    예: single + typo를 합한 CSV, 또는 single_multi_label.csv
#     repro_target = dataset_dir / "single.csv"  # 필요하면 다른 파일로 교체

#     repro_metrics = evaluate_reproducibility(
#         csv_path=repro_target,
#         results_dir=results_dir,
#         sample_n=200,   # 너무 오래 걸리면 숫자 줄이면 됨
#         num_trials=3,
#         debug_n=5,
#     )

#     # 4) 콘솔 요약 출력
#     print("\n=== 최종 요약 ===")
#     for name, m in accuracy_summary.items():
#         print(f"[Accuracy] {name}: {m['accuracy']:.4f} ({m['num_correct']}/{m['num_samples']})")

#     print(f"[Reproducibility] {repro_metrics['reproducibility']:.4f} "
#           f"({repro_metrics['num_reproducible']}/{repro_metrics['num_samples']})")


# if __name__ == "__main__":
#     main()
