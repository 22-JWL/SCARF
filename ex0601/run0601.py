import pandas as pd
from model_runner import run_model  # 사용자 정의 모델 함수
from basic_prompt import system_prompt

#===============================================================================ex1===============================================================================
# 1. 데이터 로드
df = pd.read_csv("intent_val_200.csv", encoding="cp949")

results = []
correct = 0
total_elapsed_time = 0.0  # 응답 시간 누적 변수

# 범주별 카운터
general_correct = 0
general_total = 120

irrelevant_correct = 0
irrelevant_total = 40  # 121~160

complex_correct = 0
complex_total = 40  # 161~200

# 2. 모델 실행 및 정답 비교
for idx, row in df.iterrows():
    user_input = row["text"]
    true_label = row["label"]

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

    # 범주별 정답 카운트
    if idx < 120:
        general_correct += match
    elif idx < 160:
        irrelevant_correct += match
    else:
        complex_correct += match
        
    print(f"{idx}번째 처리중")

    results.append({
        "text": user_input,
        "label": true_label,
        "generated_label": predicted_label,
        "match": match,
        "elapsed_time": elapsed_time
    })

# 3. 비교 결과 저장
result_df = pd.DataFrame(results)
result_df.to_csv("intent_label_comparison.csv", index=False, encoding="utf-8-sig")

# 4. 결과 출력
total = len(df)
accuracy_percent = round(correct / total * 100, 2)
general_percent = round(general_correct / general_total * 100, 2)
irrelevant_percent = round(irrelevant_correct / irrelevant_total * 100, 2)
complex_percent = round(complex_correct / complex_total * 100, 2)
avg_response_time = round(total_elapsed_time / total, 3)

print(f"✅ 전체 정확도: {correct}/{total} ({accuracy_percent}%)")
print(f"  └ 일반 질의 (1~120): {general_correct}/{general_total} ({general_percent}%)")
print(f"  └ 관련 없는 질의 (121~160): {irrelevant_correct}/{irrelevant_total} ({irrelevant_percent}%)")
print(f"  └ 복합 질의 (161~200): {complex_correct}/{complex_total} ({complex_percent}%)")
print(f"총 응답 시간: {round(total_elapsed_time, 2)}초")
print(f"평균 응답 시간: {avg_response_time}초")
    
    
# #===============================================================================ex2===============================================================================

# folds = [pd.read_csv(f"5fold-data/intent_5fold_part{i}.csv", encoding="cp949") for i in range(1, 6)]

# base_system_prompt = system_prompt

# def augment_system_prompt(base_prompt, wrong_list):
#     examples = [f"입력: {item['input']}\n정답: {item['label']}\n" for item in wrong_list]
#     examples_str = "".join(examples)
#     return (
#         base_prompt.rstrip() + "\n\n"
#         "다음은 출력의 예시입니다.\n"
#         f"{examples_str}"
#         '대답은 함수만 출력하고 인자는 True/False를 제외하고 ""을 꼭 붙여'
#     )

# def evaluate_fold(test_df, system_prompt, fold_idx, prompt_type):
#     results = []
#     correct = 0
#     total_elapsed_time = 0.0

#     category_total = {0: 0, 1: 0, 2: 0}
#     category_correct = {0: 0, 1: 0, 2: 0}
#     wrong_predictions = []

#     for _, row in test_df.iterrows():
#         user_input = row["text"]
#         true_label = row["label"]
#         cnum = row["cnum"]  # 0: 일반, 1: 관련없음, 2: 복합

#         try:
#             result = run_model(user_input, system_prompt=system_prompt)
#             predicted_label = result["output"]
#             elapsed_time = result["elapsed_time"]
#         except:
#             predicted_label = None
#             elapsed_time = 0.0

#         def normalize_label(s):
#             return str(s).strip().replace("\n", "").replace(" ", "")

#         match = int(normalize_label(predicted_label) == normalize_label(true_label))
        
#         correct += match 
#         total_elapsed_time += elapsed_time

#         category_total[cnum] += 1
#         category_correct[cnum] += match

#         if not match:
#             wrong_predictions.append({
#                 "input": user_input,
#                 "label": true_label
#             })

#         results.append({
#             "text": user_input,
#             "label": true_label,
#             "generated_label": predicted_label,
#             "match": match,
#             "elapsed_time": elapsed_time,
#             "cnum": cnum
#         })

#     acc = round(correct / len(test_df) * 100, 2)
#     avg_time = round(total_elapsed_time / len(test_df), 3)

#     pd.DataFrame(results).to_csv(f"fold{fold_idx+1}_result_{prompt_type}.csv", index=False, encoding="utf-8-sig")

#     print(f"\n📊 Fold {fold_idx+1} - {prompt_type} Prompt")
#     print(f"정확도: {acc}% | 평균 응답 시간: {avg_time}초")

#     label_map = {0: "일반질의", 1: "관련없는 질문", 2: "복합질의"}
#     for c in [0, 1, 2]:
#         if category_total[c] > 0:
#             cat_acc = round(category_correct[c] / category_total[c] * 100, 2)
#             print(f"  └ {label_map[c]}: {category_correct[c]}/{category_total[c]} ({cat_acc}%)")

#     print("❌ 틀린 예측:")
#     for item in wrong_predictions:
#         print(f"입력: {item['input']}\n정답: {item['label']}\n")

#     return acc

# # 전체 Fold 결과 저장용
# overall_results = []
# global_category_total = {0: 0, 1: 0, 2: 0}
# global_category_correct = {0: 0, 1: 0, 2: 0}

# for fold_idx in range(5):
#     print(f"\n🚀 Fold {fold_idx+1} 시작")

#     test_df = folds[fold_idx]
#     train_df = pd.concat([folds[i] for i in range(5) if i != fold_idx]).reset_index(drop=True)

#     wrong_examples = []
#     for _, row in train_df.iterrows():
#         try:
#             res = run_model(row["text"], system_prompt=base_system_prompt)
#             if res["output"] != row["label"]:
#                 wrong_examples.append({"input": row["text"], "label": row["label"]})
#         except:
#             continue

#     augmented_prompt = augment_system_prompt(base_system_prompt, wrong_examples)

#     # 기본 프롬프트 평가
#     print(f"\n--- 기본 프롬프트로 Fold {fold_idx+1} 테스트 ---")
#     acc_base = evaluate_fold(test_df, base_system_prompt, fold_idx, "base")

#     # 예시 포함 프롬프트 평가
#     print(f"\n--- 예시 포함 프롬프트로 Fold {fold_idx+1} 테스트 ---")
#     acc_aug = evaluate_fold(test_df, augmented_prompt, fold_idx, "augmented")

#     # 전체 cnum 정답 카운팅 누적
#     for _, row in test_df.iterrows():
#         global_category_total[row["cnum"]] += 1
#         try:
#             res = run_model(row["text"], system_prompt=augmented_prompt)
#             if res["output"] == row["label"]:
#                 global_category_correct[row["cnum"]] += 1
#         except:
#             continue

#     overall_results.append({
#         "fold": fold_idx + 1,
#         "base_accuracy": acc_base,
#         "augmented_accuracy": acc_aug
#     })

# # 결과 DataFrame
# overall_df = pd.DataFrame(overall_results)
# overall_df.to_csv("overall_fold_comparison.csv", index=False)

# # 평균 정확도
# mean_base = round(overall_df["base_accuracy"].mean(), 2)
# mean_aug = round(overall_df["augmented_accuracy"].mean(), 2)

# # 전체 cnum 기반 정확도 계산
# label_map = {0: "일반질의", 1: "관련없는 질문", 2: "복합질의"}
# print(f"\n📈 전체 평균 정확도 (기본 프롬프트): {mean_base}%")
# print(f"📈 전체 평균 정확도 (예시 포함 프롬프트): {mean_aug}%")

# print("\n🔍 전체 클래스별 정확도:")
# class_stats = []
# for c in [0, 1, 2]:
#     total = global_category_total[c]
#     correct = global_category_correct[c]
#     acc = round(correct / total * 100, 2) if total > 0 else 0.0
#     print(f"  └ {label_map[c]}: {correct}/{total} ({acc}%)")
#     class_stats.append({"class": label_map[c], "correct": correct, "total": total, "accuracy": acc})

# # 저장
# pd.DataFrame(class_stats).to_csv("overall_class_accuracy.csv", index=False, encoding="utf-8-sig")
