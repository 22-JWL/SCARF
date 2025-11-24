import json
from pathlib import Path
import pandas as pd

RESULT_DIR = Path("evaluate/results")

def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def combine_summary():
    summary_rows = []

    # 1) 정확도 요약 불러오기
    acc_path = RESULT_DIR / "accuracy_summary.json"
    if acc_path.exists():
        acc_data = load_json(acc_path)
        for name, m in acc_data.items():
            summary_rows.append({
                "dataset": name,
                "accuracy": m.get("accuracy"),
                "num_samples": m.get("num_samples"),
                "num_correct": m.get("num_correct"),
                "reproducibility": None
            })
    else:
        print("⚠ accuracy_summary.json 없음")

    # 2) 재현도 요약 불러오기
    repro_path = RESULT_DIR / "repro_summary.json"
    if repro_path.exists():
        repro_data = load_json(repro_path)
        for row in summary_rows:
            name = row["dataset"]
            if name in repro_data:
                row["reproducibility"] = repro_data[name].get("reproducibility")
    else:
        print("⚠ repro_summary.json 없음")

    df = pd.DataFrame(summary_rows)

    out_path = RESULT_DIR / "combined_summary.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print("\n📌 Combined Summary 생성 완료!")
    print(out_path)
    print(df)

if __name__ == "__main__":
    combine_summary()
