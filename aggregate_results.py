import pandas as pd
import json
import os

# 集計
def aggregate_results():
    leaderboard_data = []
    show_stats = {}

    for file in os.listdir("judges"):
        if not file.endswith(".jsonl"):
            continue

        model = file.replace("judges_", "").replace(".jsonl", "")
        results = []
        with open(f"judges/{file}", 'r', encoding='utf-8') as f:
            results = [json.loads(line) for line in f]

        # 「不明」や「エラー」を除外して正解数を計算
        valid_results = [r for r in results if r['判定'] in ["正解", "不正解"]]
        correct_count = sum(1 for r in valid_results if r['判定'] == '正解')
        total_questions = len(valid_results)
        accuracy = correct_count / total_questions if total_questions > 0 else 0

        leaderboard_data.append({
            "モデル": model,
            "正解率": accuracy,
            "正解数": correct_count,
            "総問題数": total_questions
        })

        # 番組ごとの正解率
        show_counts = {}
        for result in valid_results:
            show = result['番組名']
            if show not in show_counts:
                show_counts[show] = {"correct": 0, "total": 0}
            show_counts[show]["total"] += 1
            if result['判定'] == '正解':
                show_counts[show]["correct"] += 1
        
        show_stats[model] = {show: stats["correct"] / stats["total"] for show, stats in show_counts.items()}

    # リーダーボードCSV（正解率で降順ソート）
    leaderboard_df = pd.DataFrame(leaderboard_data)
    leaderboard_df = leaderboard_df.sort_values(by="正解率", ascending=False)  # ここでソート
    leaderboard_df.to_csv("leaderboard.csv", index=False, encoding='utf-8-sig')

    # 番組ごとの正解率をピボット形式でCSV出力
    show_stats_df = pd.DataFrame(show_stats).T.reset_index()
    show_stats_df = show_stats_df.rename(columns={'index': 'モデル'})
    show_stats_df.fillna(0, inplace=True)
    show_stats_df.to_csv("show_stats.csv", index=False, encoding='utf-8-sig')

    print("集計結果を leaderboard.csv と show_stats.csv に保存しました。")

if __name__ == "__main__":
    aggregate_results()