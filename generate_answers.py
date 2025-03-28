import random
import litellm
import pandas as pd
import json
from litellm import completion
import os
import argparse
import time
from datasets import load_dataset

# エラーリトライ付きの回答生成
def generate_answer(model, question, api_base=None, api_key=None, retries=10, backoff_factor=3):  # デフォルトのbackoff_factorを5に
    for attempt in range(retries):
        try:
            response = completion(
                model=model,
                api_base=api_base,
                api_key=api_key,
                messages=[
                    {"role": "system", "content": "あなたはアニメの知識を持つAIです。質問に簡潔に答えてください。"},
                    {"role": "user", "content": question}
                ],
                max_tokens=100,
                temperature=0.2
            )
            if response and response.choices and len(response.choices) > 0 and response.choices[0].message and hasattr(response.choices[0].message, 'content'):
                return response.choices[0].message.content.strip()
            else:
                print(f"Attempt {attempt + 1}: Invalid response structure.")
                return "エラー(無効なレスポンス構造)"

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                wait_time = (backoff_factor ** attempt) + (random.random() * 0.5)  # 指数バックオフ
                print(f"Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                print("Max retries reached.")
                return "エラー(最大リトライ到達)"

    return "エラー(不明なエラー)" # ここには到達しないはずだが、念のため

# Hugging Face データセットからクイズをロード
def load_quiz_from_hf(quiz_csv="Ani-Bench.csv"):
    # if os.path.exists(quiz_csv):
    #     return pd.read_csv(quiz_csv)
    # else:
    dataset = load_dataset("umiyuki/Ani-Bench-JP", split="test")
    return pd.DataFrame(dataset)

# 回答生成
def generate_answers(model_name, provider, api_base=None, api_key=None):
    # モデル名にプロバイダを付加
    full_model_name = f"{provider}/{model_name}" if provider else model_name
    print(f"Using model: {full_model_name}")
    if api_base:
        print(f"Using API base: {api_base}")
    # APIキーがダミーかどうか表示（デバッグ用）
    print(f"Using API key: {'*' * (len(api_key) - 3) + api_key[-3:] if api_key and api_key != 'dummy_key' else api_key}")

    # Hugging Face からクイズをロード
    quiz_df = load_quiz_from_hf()
    if quiz_df.empty:
        print("No quiz data loaded. Exiting.")
        return
    
    # 期待される列名が存在するか確認
    required_columns = ['問題', '答え', '番組名']
    if not all(col in quiz_df.columns for col in required_columns):
        print(f"Error: Missing required columns in quiz data. Expected: {required_columns}, Found: {list(quiz_df.columns)}")
        # 存在しない列がある場合、処理を中断するか、代替処理を行う
        # ここでは例としてプログラムを終了
        return 

    results = []
    total_questions = len(quiz_df)
    print(f"Generating answers for {total_questions} questions...")
    for idx, row in quiz_df.iterrows():
        # rowが辞書ライクなオブジェクトであることを確認
        try:
            question = row['問題']
            correct_answer = row['答え']
            show_name = row['番組名']
        except KeyError as e:
            print(f"Skipping row {idx} due to missing key: {e}")
            continue
        except TypeError:
             print(f"Skipping row {idx} because it's not a dictionary-like object: {row}")
             continue


        print(f"Processing question {idx + 1}/{total_questions}: {question[:50]}...") # 進捗表示

        prompt = f"アニメ、{show_name}の問題です。{question}"
        # generate_answerにapi_keyを渡す
        llm_answer = generate_answer(full_model_name, prompt, api_base, api_key)

        result = {
            "問題": question,
            "正解": correct_answer,
            "番組名": show_name,
            "LLM回答": llm_answer
        }
        results.append(result)

    # answersフォルダに保存
    os.makedirs("answers", exist_ok=True)
    output_file = f"answers/answers_{model_name.replace('/', '__')}.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    print(f"回答を {output_file} に保存しました。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate answers for quiz using specified LLM.")
    parser.add_argument("--model", required=True, help="Model name (e.g., rinna/bakeneko-32b)")
    parser.add_argument("--provider", default=None, help="Provider name (e.g., openai)")
    parser.add_argument("--api_base", default=None, help="API base URL (optional)")
     # --api_key引数を追加し、デフォルト値を"dummy_key"に設定
    parser.add_argument("--api_key", default="dummy_key", help="API key for the LLM provider (optional, defaults to 'dummy_key')")
    args = parser.parse_args()
    #litellm._turn_on_debug()
    generate_answers(args.model, args.provider, args.api_base, args.api_key)