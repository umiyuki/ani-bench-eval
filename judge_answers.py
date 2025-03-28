import json
from litellm import completion
import os
import argparse
import time
import random

# エラーリトライ付きのジャッジ
def judge_answer(model, question, correct_answer, llm_answer, api_base=None, api_key=None, retries=10, backoff_factor=2):  # デフォルトのbackoff_factorを5に
    prompt = f"""
    以下の質問に対する正解とLLMの回答を比較し、同じ意味であれば「正解」、異なれば「不正解」と判定してください。
    質問: {question}
    正解: {correct_answer}
    LLMの回答: {llm_answer}
    判定結果を「正解」または「不正解」のいずれか一言のみで返してください。他の言葉は含めないでください。
    """
    for attempt in range(retries):
        try:
            response = completion(
                model=model,
                api_base=api_base,
                api_key=api_key,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.0
            )
            if response and response.choices and len(response.choices) > 0 and response.choices[0].message and hasattr(response.choices[0].message, 'content'):
                result = response.choices[0].message.content.strip()
                if "不正解" in result:
                    return "不正解"
                elif "正解" in result:
                    return "正解"
                else:
                    print(f"Attempt {attempt + 1}: Unexpected judge response: {result}")
                    if attempt == retries - 1:
                        return "不明(予期せぬ応答)"
            else:
                print(f"Attempt {attempt + 1}: Invalid response structure.")
                if attempt == retries - 1:
                    return "エラー(無効なレスポンス構造)"

        except Exception as e:
            print(f"Judge Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                wait_time = (backoff_factor ** attempt) + (random.random() * 0.5)  # 指数バックオフ
                print(f"Retrying judge in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                print("Max judge retries reached.")
                return "エラー(最大リトライ到達)"
    return "エラー(判定失敗)"

# 回答ジャッジ
def judge_answers(model_name, judge_model, judge_api_base=None, judge_api_key=None, backoff_factor=2):
    input_file = f"answers/answers_{model_name.replace('/', '__')}.jsonl"
    print(f"Loading answers from: {input_file}")
    if not os.path.exists(input_file):
        print(f"Error: Input file not found at {input_file}")
        return

    print(f"Using judge model: {judge_model}")
    if judge_api_base:
        print(f"Using judge API base: {judge_api_base}")
    print(f"Using judge API key: {'*' * (len(judge_api_key) - 3) + judge_api_key[-3:] if judge_api_key and judge_api_key != 'dummy_key' else judge_api_key}")

    results = []
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            total_lines = len(lines)
            print(f"Judging {total_lines} answers...")

            for i, line in enumerate(lines):
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"Skipping line {i+1} due to JSON decode error: {e}")
                    continue

                required_keys = ['問題', '正解', 'LLM回答', '番組名']
                if not all(key in data for key in required_keys):
                    print(f"Skipping line {i+1} due to missing keys. Found: {list(data.keys())}")
                    continue

                question = data['問題']
                correct_answer = data['正解']
                llm_answer = data['LLM回答']
                show_name = data['番組名']

                if not llm_answer or llm_answer.startswith("エラー"):
                    judgment = "判定不可(LLMエラー)"
                    print(f"Skipping judgment for line {i+1} due to LLM error in answer.")
                else:
                    print(f"Judging answer {i + 1}/{total_lines}...")
                    judgment = judge_answer(judge_model, question, correct_answer, llm_answer, judge_api_base, judge_api_key, backoff_factor=backoff_factor)

                result = {
                    "問題": question,
                    "正解": correct_answer,
                    "番組名": show_name,
                    "LLM回答": llm_answer,
                    "判定": judgment
                }
                results.append(result)

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file}")
        return
    except Exception as e:
        print(f"An unexpected error occurred while reading {input_file}: {e}")
        return

    # judgesフォルダに保存
    os.makedirs("judges", exist_ok=True)
    safe_model_name = model_name.replace('/', '__')
    output_file = f"judges/judges_{safe_model_name}.jsonl"

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        print(f"ジャッジ結果を {output_file} に保存しました。")
    except IOError as e:
        print(f"Error writing to file {output_file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Judge answers using specified LLM.")
    parser.add_argument("--model", required=True, help="Model name whose answers are being judged (e.g., gpt-3.5-turbo, used for input filename)")
    parser.add_argument("--judge_model", required=True, help="Judge model name (e.g., gpt-4o)")
    parser.add_argument("--judge_api_base", default=None, help="Judge API base URL (optional)")
    parser.add_argument("--judge_api_key", default="dummy_key", help="API key for the judge LLM provider (optional)")
    parser.add_argument("--backoff_factor", type=int, default=2, help="Backoff factor for retry delays (default: 2)")  # backoff_factorを引数に追加
    args = parser.parse_args()

    # judge_answers に backoff_factor を渡す
    judge_answers(args.model, args.judge_model, args.judge_api_base, args.judge_api_key, args.backoff_factor)