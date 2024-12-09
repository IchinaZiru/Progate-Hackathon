import json
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import openai
import os
import subprocess
from dotenv import load_dotenv

# 環境変数をロード
load_dotenv()

app = FastAPI()

# CORS設定を追加
origins = [
    "",  # 自分のフロントエンド URL（例: Reactなどの開発用サーバー）
    "",  # 例えば React が動作しているポート
    "http://127.0.0.1:8000",  # その他のローカルホストの設定
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 許可するオリジン
    allow_credentials=True,
    allow_methods=["*"],  # 全てのHTTPメソッドを許可
    allow_headers=["*"],  # 全てのヘッダーを許可
)

# OpenAI API キーを設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OpenAI APIキーが設定されていません。環境変数 'OPENAI_API_KEY' を確認してください。")
openai.api_key = OPENAI_API_KEY

# 会話履歴ファイル
HISTORY_FILE = "conversation_history.json"

# 会話履歴をロードする関数
def load_conversation_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 会話履歴を保存する関数
def save_conversation_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

# 初期会話履歴をロード
conversation_history = load_conversation_history()

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>AI Chat Backend</title>
        </head>
        <body>
            <h1>FastAPI サーバーが動作しています！</h1>
            <p>WebSocket エンドポイント: /ws</p>
        </body>
    </html>
    """

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global conversation_history
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            print(f"ユーザーからの入力: {data}")

            if data.lower() == "終了":
                save_conversation_history(conversation_history)  # 終了時に会話履歴を保存
                await websocket.close()
                break

            # 特別なキーワード処理
            if data.lower() in ["おやすみ", "おはよう"]:
                await websocket.send_text(data)  # フロントエンドにそのまま通知
                continue

            # "じゃんけんしよ" というキーワードが入力された場合、Python スクリプトを実行
            if "じゃんけんしよ" in data:
                script_name = "./backend/RSPGame.py"  # 実行したい Python スクリプトの名前
                script_path = os.path.join(os.getcwd(), script_name)

                try:
                    result = subprocess.run(['python', script_path], capture_output=True, text=True)
                    if result.returncode == 0:
                        await websocket.send_text(f"コード実行結果:\n{result.stdout}")
                    else:
                        await websocket.send_text(f"コード実行中にエラーが発生しました:\n{result.stderr}")
                except Exception as e:
                    await websocket.send_text(f"スクリプト実行エラー: {e}")
                continue  # "実行" キーワードが含まれている場合は、OpenAI APIへのリクエストをスキップ

            # "音楽流して" というキーワードが入力された場合、Python スクリプトを実行
            if "音楽流して" in data:
                script_name = "./backend/spotify.py"  # 実行したい Python スクリプトの名前
                script_path = os.path.join(os.getcwd(), script_name)

                try:
                    result = subprocess.run(['python', script_path], capture_output=True, text=True)
                    if result.returncode == 0:
                        await websocket.send_text(f"コード実行結果:\n{result.stdout}")
                    else:
                        await websocket.send_text(f"コード実行中にエラーが発生しました:\n{result.stderr}")
                except Exception as e:
                    await websocket.send_text(f"スクリプト実行エラー: {e}")
                continue  # "実行" キーワードが含まれている場合は、OpenAI APIへのリクエストをスキップ

            # "天気" というキーワードが入力された場合、Python スクリプトを実行
            elif "天気" in data:
                script_name = "./backend/Weather.py"  # 実行したい Python スクリプトの名前
                script_path = os.path.join(os.getcwd(), script_name)

                try:
                    result = subprocess.run(['python', script_path], capture_output=True, text=True)
                    if result.returncode == 0:
                        await websocket.send_text(f"コード実行結果:\n{result.stdout}")
                    else:
                        await websocket.send_text(f"コード実行中にエラーが発生しました:\n{result.stderr}")
                except Exception as e:
                    await websocket.send_text(f"スクリプト実行エラー: {e}")
                continue  # "実行" キーワードが含まれている場合は、OpenAI APIへのリクエストをスキップ

            # OpenAI APIへのリクエスト
            try:
                # 履歴に新しいメッセージを追加
                conversation_history.append({"role": "user", "content": data})

                # APIリクエスト
                response = openai.ChatCompletion.create(
                    model="",
                    messages=[{"role": "system", "content": "あなたは親切なアシスタントです。"}] + conversation_history
                )
                ai_response = response['choices'][0]['message']['content']
                print(f"OpenAIからの応答: {ai_response}")

                # 履歴にAIの応答を追加
                conversation_history.append({"role": "assistant", "content": ai_response})

                # ユーザーに応答を送信
                await websocket.send_text(ai_response)

                # 履歴を即座に保存
                save_conversation_history(conversation_history)

            except openai.error.OpenAIError as e:
                print(f"OpenAI APIエラー: {e}")
                await websocket.send_text("AI応答の生成中にエラーが発生しました。")
    except Exception as e:
        print(f"WebSocket エラー: {e}")
