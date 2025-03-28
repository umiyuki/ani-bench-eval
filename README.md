# Ani-Bench Evaluation

`Ani-Bench` は、アニメに関する知識を測定するための LLM (Large Language Model) ベンチマークです。このリポジトリ `ani-bench-eval` には、Hugging Face データセット `Ani-Bench-JP` を使用して LLM を評価するためのスクリプトが含まれています。

- **データセット**: [umiyuki/Ani-Bench-JP](https://huggingface.co/datasets/umiyuki/Ani-Bench-JP) (`test` スプリットを使用)
- **目的**: 複数の LLM のアニメ知識を比較し、リーダーボード形式で結果をまとめる。

## 特徴
- **柔軟なモデル評価**: LiteLLM を使用して、さまざまな LLM を統合的に評価可能。
- **自動ジャッジ**: LLM as a Judge 方式で回答の正誤を判定（意味的な一致も考慮）。
- **リーダーボード**: モデルごとおよび番組ごとの正解率を CSV で出力。

## セットアップ手順

### 前提条件
- Python 3.8 以上
- [uv](https://github.com/astral-sh/uv)（依存関係管理ツール）
- Git

### 1. リポジトリのクローン
```bash
git clone https://github.com/umiyuki/ani-bench-eval.git
cd ani-bench-eval
```

### 2. 仮想環境の作成、依存関係のインストール
`uv` を使用して仮想環境を同期します。
```bash
uv sync
```

仮想環境を有効化します：
- Linux/macOS:
  ```bash
  source .venv/bin/activate
  ```
- Windows:
  ```bash
  .venv\Scripts\activate
  ```

uvを使いたくない場合
手動で仮想環境を作成して、必要なライブラリをインストールします。
```bash
python -m venv .venv
.venv/bin/activate
pip install litellm pandas datasets
```

## 評価手順

### 1. 回答の生成
`generate_answers.py` を使って、指定した LLM でクイズに対する回答を生成します。生成結果は `answers/` フォルダに保存されます。

#### 実行例
Llama.cppサーバでロードしたモデルを評価する場合（--providerをopenaiにして、--api_baseを設定するとOpenAI互換サーバを評価できます）
```bash
python generate_answers.py --model google/gemma-3-12b-it --provider openai --api_base http://127.0.0.1:8080
```
- `--model`: 評価するモデル名（例: `google/gemma-3-12b-it`）。
- `--provider`: プロバイダ名（例: `openai`）。指定すると `openai/google/gemma-3-12b-it` のように結合されます。
- `--api_base`: API エンドポイントの URL（オプション）。
- `--api_key`: API キー（オプション。未指定時はダミーキーが使用されます）。

出力ファイル: `answers/answers_google__gemma-3-12b-it.jsonl`

gemini-2.0-flash-expのモデルを評価する場合（GoogleAIStudioのAPIキーを入力する）
```bash
python generate_answers.py --model gemini-2.0-flash-exp --provider gemini --api_key your_api_key
```

### 2. 回答のジャッジ
`judge_answers.py` を使って、生成された回答を別の LLM で判定します。結果は `judges/` フォルダに保存されます。

#### 実行例
gemini-2.0-flash-expにジャッジしてもらう場合（GoogleAIStudioのAPIキーを入力する）
```bash
python judge_answers.py --model google/gemma-3-12b-it --judge_model gemini/gemini-2.0-flash-exp --judge_api_key your_judge_api_key
```
- `--model`: 判定対象のモデル名（`answers/` フォルダのファイル名と一致）。
- `--judge_model`: ジャッジに使用するモデル名（例: `gemini/gemini-2.0-flash-exp`）。通常のLiteLLMのモデル名指定に従います。
- `--judge_api_base`: ジャッジ用 API のエンドポイント（オプション）。
- `--judge_api_key`: ジャッジ用 API キー（オプション。未指定時はダミーキーが使用されます）。

出力例: `judges/judges_google_gemma-3-12b-it.jsonl`

### 3. 結果の集計
`aggregate_results.py` を使って、ジャッジ結果を集計し、リーダーボードと番組ごとの統計を生成します。

#### 実行例
```bash
python aggregate_results.py
```
- 引数は不要。`judges/` フォルダ内の全 `.jsonl` ファイルを自動的に集計。

#### 出力
- `leaderboard.csv`: モデルごとの全体正解率。
  ```
  モデル,正解率,正解数,総問題数
  google_gemma-3-12b-it,0.8667,26,30
  ```
- `show_stats.csv`: モデルごと・番組ごとの正解率。
  ```
  モデル,魔法少女まどか☆マギカ,ぼっちざろっく,機動戦士ガンダム
  google_gemma-3-12b-it,0.8667,0.0,0.0
  ```

## 注意点
- **データセット**: `Ani-Bench-JP` の `test` スプリットを使用します。
- **エラーリトライ**: API 呼び出しに失敗した場合、最大10回リトライします。
- **不明判定**: ジャッジ結果が「正解」または「不正解」でない場合、「不明」として集計から除外されます。

## ライセンス
MIT License