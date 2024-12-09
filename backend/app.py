import tkinter as tk
from tkinter import Canvas, Frame
import asyncio
import websockets
import threading
import speech_recognition as sr
from gtts import gTTS
import tempfile
import pygame
import os  # os モジュールをインポート
import time

# WebSocket のエンドポイント
WS_URL = "ws://127.0.0.1:8000/ws"

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LINE風 AI チャット")
        self.root.geometry("800x600")  # 初期サイズ
        self.root.configure(bg="#E5E5E5")

        # フラグ: スリープモードかどうか
        self.sleep_mode = False
        self.in_speech_recognition = False  # 音声認識中かどうかのフラグ

        # 全画面表示対応
        self.root.attributes('-fullscreen', True)  # フルスクリーンモードを有効にする
        self.root.bind("<Escape>", lambda e: self.root.attributes('-fullscreen', False))  # Escキーで解除可能

        # チャット表示エリア
        self.chat_frame = tk.Frame(self.root, bg="#E5E5E5")
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # キャンバスを使用してスクロール可能に
        self.canvas = Canvas(self.chat_frame, bg="#E5E5E5", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.chat_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#E5E5E5")

        self.scrollable_frame.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 赤い線の設定
        self.red_line = tk.Frame(self.root, bg="red", height=5)
        self.red_line.pack(fill=tk.X, side=tk.BOTTOM)

        # 赤い線の点滅スレッド
        self.blinking = True
        threading.Thread(target=self._blink_red_line, daemon=True).start()

        # ウィンドウサイズ変更時の動作
        self.root.bind("<Configure>", self.on_resize)

        # WebSocket 接続を非同期で開始
        self.websocket = None
        self.loop = asyncio.get_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        asyncio.run_coroutine_threadsafe(self.connect_websocket(), self.loop)

        # 初回の音声認識を開始
        self.start_speech_recognition()

        # pygame の初期化
        pygame.mixer.init()

    def add_message(self, message, sender="User"):
        """
        メッセージを追加（LINE風デザイン）
        スリープモード中にチャットの背景色と文字色を変更
        """
        # スリープモードかどうかで背景色と文字色を変更
        if self.sleep_mode:
            bubble_color = "#333333"  # スリープモードではダークな背景
            text_color = "#FFFFFF"  # 文字色を白に変更
        else:
            bubble_color = "#FFFFFF" if sender == "User" else "#DCF8C6"
            text_color = "#000000"  # 通常時の文字色は黒

        anchor = "e" if sender == "User" else "w"

        bubble = tk.Frame(self.scrollable_frame, bg=bubble_color, bd=0)
        bubble.pack(anchor=anchor, pady=10, padx=10, fill=tk.X)  # 横幅をフルに広げる設定

        text = tk.Label(
            bubble,
            text=message,
            bg=bubble_color,
            fg=text_color,
            wraplength=self.root.winfo_width() * 0.9,  # ウィンドウ幅の90%に収める
            justify="left" if sender == "AI" else "right",
            padx=20,
            pady=20,
            font=("Arial", 24)  # 文字サイズをさらに大きく設定
        )
        text.pack(fill=tk.X, expand=True)  # バブル内で文字を横に広げる

        # スクロールを最下部に移動
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    async def connect_websocket(self):
        """
        WebSocket 接続
        """
        try:
            self.websocket = await websockets.connect(WS_URL)
            self.add_message("WebSocket 接続成功", "System")
            asyncio.create_task(self.receive_messages())
        except Exception as e:
            self.add_message(f"WebSocket 接続失敗: {e}", "System")

    async def receive_messages(self):
        """
        WebSocket メッセージ受信
        """
        while self.websocket:
            try:
                response = await self.websocket.recv()
                self.add_message(response, "AI")
                # AIの応答を読み上げ
                self.speak_text(response)
                # AIの応答後に音声認識を再開
                self.start_speech_recognition()
            except Exception as e:
                self.add_message(f"メッセージ受信エラー: {e}", "System")
                break

    def send_message(self, message):
        """
        WebSocket を通じてメッセージを送信
        """
        if self.websocket:
            asyncio.run_coroutine_threadsafe(self.websocket.send(message), self.loop)
            self.add_message(message, "User")

    def start_speech_recognition(self):
        """
        音声認識を開始
        """
        if not self.in_speech_recognition:
            threading.Thread(target=self._speech_recognition, daemon=True).start()

    def _speech_recognition(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            self.in_speech_recognition = True  # 音声認識中フラグを立てる
            while True:  # スリープモード中も音声認識を続ける
                try:
                    recognizer.adjust_for_ambient_noise(source)
                    audio = recognizer.listen(source, timeout=600)

                    # 音声入力が「おやすみ」または「おはよう」の場合
                    message = recognizer.recognize_google(audio, language="ja-JP")
                    print(f"音声認識結果: {message}")

                    if "おやすみ" in message:
                        self.activate_sleep_mode()
                    elif "おはよう" in message:
                        self.deactivate_sleep_mode()

                    elif not self.sleep_mode:  # スリープモード中でない場合にメッセージ送信
                        self.root.after(0, self.send_message, message)

                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    self.add_message(f"音声認識エラー: {e}", "System")
                    continue
                finally:
                    self.in_speech_recognition = False  # 音声認識が終わったのでフラグを戻す

    def speak_text(self, text):
        """
        テキストを読み上げる
        """
        try:
            tts = gTTS(text=text, lang="ja")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                temp_path = temp_file.name
            tts.save(temp_path)

            # pygame で音声を再生
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)  # 再生が終わるまで待機

            pygame.mixer.music.unload()  # ファイルをアンロードして削除可能にする
            os.remove(temp_path)  # 再生後に一時ファイルを削除
        except Exception as e:
            self.add_message(f"読み上げエラー: {e}", "System")

    def _blink_red_line(self):
        """
        赤い線を点滅させる
        """
        while self.blinking:
            self.red_line.configure(bg="red")
            time.sleep(0.5)
            self.red_line.configure(bg="#E5E5E5")  # 背景色と同じ色にして点滅を実現
            time.sleep(0.5)

    def on_resize(self, event):
        """
        ウィンドウサイズ変更時
        """
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def set_chat_background(self, color):
        """
        チャット画面の背景色を動的に変更
        """
        self.chat_frame.configure(bg=color)
        self.canvas.configure(bg=color)
        self.scrollable_frame.configure(bg=color)

    def activate_sleep_mode(self):
        """
        スリープモードを有効化
        チャットエリアのサイズを小さくする
        """
        self.sleep_mode = True
        self.set_chat_background("#333333")  # チャット背景色をダークに変更
        self.red_line.configure(bg="#E5E5E5")  # 赤い線を非表示に
        self.add_message("スリープモードが有効になりました", "System")

    def deactivate_sleep_mode(self):
        """
        スリープモードを解除
        チャット背景色を元に戻す
        """
        self.sleep_mode = False
        self.set_chat_background("#E5E5E5")  # 元の背景色に戻す
        self.red_line.configure(bg="red")  # 赤い線を再表示
        self.add_message("スリープモードが解除されました", "System")


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()
