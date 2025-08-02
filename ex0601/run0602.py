import pandas as pd
from model_runner import run_model  # 사용자 정의 모델 함수
from prompt_combine_none import system_prompt

base_system_prompt = system_prompt
label_map = {0: "일반질의", 1: "관련없는 질문", 2: "복합질의"}

# 5개의 fold 데이터 로드 (각각 40개)
folds = [pd.read_csv(f"5fold-data/intent_5fold_part{i}.csv", encoding="cp949") for i in range(1, 6)]

# 프롬프트 확장
def augment_system_prompt(base_prompt, wrong_list):
    examples = [f"입력: {item['input']}\n정답: {item['label']}\n" for item in wrong_list]
    examples_str = "".join(examples)
    return (
        base_prompt.rstrip() + "\n\n"
        "다음은 출력의 예시입니다.\n"
        f"{examples_str}"
    )

# 평가 함수
def evaluate(df, system_prompt, fold_idx, prompt_type):
    correct = 0
    total_elapsed_time = 0.0
    category_total = {0: 0, 1: 0, 2: 0}
    category_correct = {0: 0, 1: 0, 2: 0}

    results = []

    for idx, row in df.iterrows():
        user_input = row["text"]
        true_label = row["label"]
        cnum = row["cnum"]

        try:
            result = run_model(user_input, system_prompt)
            predicted_label = result["output"]
            elapsed_time = result["elapsed_time"]
        except:
            predicted_label = None
            elapsed_time = 0.0

        def normalize_label(s):
            return str(s).strip().replace("\n", "").replace(" ", "")

        match = int(normalize_label(predicted_label) == normalize_label(true_label))
        correct += match
        total_elapsed_time += elapsed_time
        category_total[cnum] += 1
        category_correct[cnum] += match

        results.append({
            "text": user_input,
            "label": true_label,
            "generated_label": predicted_label,
            "match": match,
            "elapsed_time": elapsed_time,
            "cnum": cnum
        })

    df_result = pd.DataFrame(results)
    df_result.to_csv(f"fold{fold_idx+1}_{prompt_type}_result.csv", index=False, encoding="utf-8-sig")

    acc = round(correct / len(df) * 100, 2)
    avg_time = round(total_elapsed_time / len(df), 3)
    print(f"\n📊 Fold {fold_idx+1} - {prompt_type.upper()} Prompt")
    print(f"정확도: {acc}% | 평균 응답 시간: {avg_time}초")

    for c in [0, 1, 2]:
        if category_total[c] > 0:
            cat_acc = round(category_correct[c] / category_total[c] * 100, 2)
            print(f"  └ {label_map[c]}: {category_correct[c]}/{category_total[c]} ({cat_acc}%)")

    return {
        "accuracy": acc,
        "avg_time": avg_time,
        "category_correct": category_correct,
        "category_total": category_total
    }

# 전체 결과 저장
all_results = []
category_accumulator = {0: {"correct": 0, "total": 0},
                        1: {"correct": 0, "total": 0},
                        2: {"correct": 0, "total": 0}}
category_accumulator_base = {0: {"correct": 0, "total": 0},
                             1: {"correct": 0, "total": 0},
                             2: {"correct": 0, "total": 0}}

for fold_idx in range(5):
    print(f"\n🚀 Fold {fold_idx+1} 시작")

    test_df = folds[fold_idx]
    train_dfs = [folds[i] for i in range(5) if i != fold_idx]
    train_df = pd.concat(train_dfs).reset_index(drop=True)

    # 오답 수집
    wrong_examples = []
    for _, row in train_df.iterrows():
        try:
            res = run_model(row["text"], system_prompt=base_system_prompt)
            if res["output"] != row["label"]:
                wrong_examples.append({"input": row["text"], "label": row["label"]})
        except:
            continue

    # 프롬프트 생성
    augmented_prompt = augment_system_prompt(base_system_prompt, wrong_examples)

    # base prompt 평가
    res_base = evaluate(test_df, base_system_prompt, fold_idx, "base")

    # augmented prompt 평가
    res_aug = evaluate(test_df, augmented_prompt, fold_idx, "augmented")

    # 결과 누적
    all_results.append({
        "fold": fold_idx + 1,
        "base_accuracy": res_base["accuracy"],
        "augmented_accuracy": res_aug["accuracy"]
    })

    # 클래스별 누적
    for c in [0, 1, 2]:
        category_accumulator[c]["correct"] += res_aug["category_correct"][c]
        category_accumulator[c]["total"] += res_aug["category_total"][c]
        category_accumulator_base[c]["correct"] += res_base["category_correct"][c]
        category_accumulator_base[c]["total"] += res_base["category_total"][c]

# 결과 저장
overall_df = pd.DataFrame(all_results)
overall_df.to_csv("fold_prompt_comparison.csv", index=False, encoding="utf-8-sig")

# 평균 정확도
mean_base = round(overall_df["base_accuracy"].mean(), 2)
mean_aug = round(overall_df["augmented_accuracy"].mean(), 2)

print(f"\n✅ 전체 평균 정확도")
print(f"  - Base Prompt: {mean_base}%")
print(f"  - Augmented Prompt: {mean_aug}%")

print(f"\n📈 전체 클래스별 정확도 (Augmented Prompt 기준)")
for c in [0, 1, 2]:
    total = category_accumulator[c]["total"]
    correct = category_accumulator[c]["correct"]
    acc = round(correct / total * 100, 2) if total else 0.0
    print(f"  └ {label_map[c]}: {correct}/{total} ({acc}%)")

print(f"\n📉 전체 클래스별 정확도 (Base Prompt 기준)")
for c in [0, 1, 2]:
    total = category_accumulator_base[c]["total"]
    correct = category_accumulator_base[c]["correct"]
    acc = round(correct / total * 100, 2) if total else 0.0
    print(f"  └ {label_map[c]}: {correct}/{total} ({acc}%)")

