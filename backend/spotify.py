import openai
import requests
import re
import speech_recognition as sr
from gtts import gTTS
import os
import webbrowser
import time
import tempfile
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import sys
from playsound import playsound  # playsoundライブラリをインポート
import pyautogui  # pyautoguiをインポート
import pyautogui
import pygetwindow as gw

# 環境変数をロード
load_dotenv()

# ウィンドウタイトルに基づいて対象を特定
window_title = "Spotify"  # 例: "メモ帳"
target_window = None


# Spotipyクライアントのセットアップ
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv('SPOTIFY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
    redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
    scope="user-read-playback-state user-modify-playback-state"
))

def speak_text(text):
    """指定されたテキストを音声で出力"""
    print(f"【音声出力】: {text}")
    tts = gTTS(text=text, lang='ja')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        temp_file_path = temp_file.name
    tts.save(temp_file_path)
    playsound(temp_file_path)  # playsoundで音声を再生
    os.remove(temp_file_path)

def recognize_speech():
    """音声入力を認識し、文字列として返す"""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        speak_text("音声をお話しください...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio, language="ja-JP")
            speak_text(f"認識された音声: {text}")
            return text
        except sr.UnknownValueError:
            speak_text("音声が認識できませんでした。もう一度お話しください。")
            return ""
        except sr.RequestError:
            speak_text("音声認識サービスに接続できません。")
            return ""

def open_spotify_web_app():
    """Spotify Webアプリを開く"""
    url = "https://open.spotify.com"
    chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe %s"
    speak_text("Spotify Webアプリを開きます。")
    webbrowser.get(chrome_path).open(url)
    time.sleep(3)

def choose_device():
    """利用可能なデバイスを選択"""
    devices = sp.devices()
    if not devices['devices']:
        speak_text("利用可能なデバイスが見つかりませんでした。")
        return None

    speak_text("利用可能なデバイスを取得しました。")
    for idx, device in enumerate(devices['devices']):
        speak_text(f"{idx + 1}番. {device['name']} ({device['type']})")
        print(f"{idx + 1}番. {device['name']} ({device['type']})")

    while True:
        speak_text("デバイスを選択してください。")
        user_choice = recognize_speech()

        # 音声認識結果から「番」を取り除く
        user_choice = re.sub(r'番', '', user_choice).strip()

        # 音声認識が成功し、数字の入力かどうかをチェック
        if user_choice.isdigit():
            choice = int(user_choice) - 1
            if 0 <= choice < len(devices['devices']):
                selected_device = devices['devices'][choice]
                speak_text(f"{selected_device['name']} を選択しました。")
                return selected_device['id']
            else:
                speak_text("無効な選択です。もう一度選択をお願いします。")
        else:
            speak_text("無効な入力です。番号を再度言ってください。")


def search_and_play(device_id):
    """楽曲を検索して再生"""
    speak_text("再生する楽曲を検索してください。")
    query = recognize_speech()

    # 空のクエリが返された場合、再度入力を促す
    if not query.strip():
        speak_text("検索クエリが空です。もう一度楽曲名をお話しください。")
        return search_and_play(device_id)  # 再度検索

    # ユーザーに認識されたクエリを確認させる
    speak_text(f"認識された楽曲は「{query}」です。これでよろしいですか？")
    confirmation = recognize_speech()

    if "はい" in confirmation:
        results = sp.search(q=query, type='track', limit=5)

        if not results['tracks']['items']:
            speak_text("楽曲が見つかりませんでした。")
            return

        speak_text("検索結果を表示します。")
        for idx, track in enumerate(results['tracks']['items']):
            track_info = f"{idx + 1}番. {track['name']} by {', '.join(artist['name'] for artist in track['artists'])}"
            print(track_info)

        while True:
            speak_text("再生する楽曲を選択してください。")
            user_choice = recognize_speech()

            # 音声認識結果から「番」を取り除く
            user_choice = re.sub(r'番', '', user_choice).strip()

            # 音声認識が成功し、数字の入力かどうかをチェック
            if user_choice.strip().isdigit():
                choice = int(user_choice) - 1
                if 0 <= choice < len(results['tracks']['items']):
                    track_uri = results['tracks']['items'][choice]['uri']
                    track = results['tracks']['items'][choice]
                    sp.start_playback(device_id=device_id, uris=[track_uri])
                    speak_text(f"{track['name']} を再生します。")
                    break  # 楽曲再生後、選択終了
                else:
                    speak_text("無効な選択です。もう一度選択をお願いします。")
            else:
                speak_text("無効な入力です。番号を再度言ってください。")
    else:
        speak_text("もう一度楽曲名をお話しください。")
        search_and_play(device_id)  # 再度楽曲検索を促す

def playback_controls():
    """再生コントロール"""
    commands = {
        "停止": sp.pause_playback,
        "再開": sp.start_playback,
        "次": sp.next_track,
        "前": sp.previous_track,
    }

    while True:
        print("コマンドを言ってください。再生停止、次、前など。終了するには終了と言ってください。")
        command = recognize_speech()
        if "終了" in command:
            speak_text("プログラムを終了します。")
            pyautogui.hotkey('alt', 'f4')  # Alt + F4を送信してChromeを閉じる
            sys.exit()  # プログラムを終了
        if "再生コントロール終了" in command:
            speak_text("再生コントロールを終了します。")
            break  # 再生コントロールのみ終了
        for key, action in commands.items():
            if key in command:
                action()
                speak_text(f"{key}しました。")
                break

def main():
    speak_text("Spotifyを起動するには、'起動' と言ってください。")

    while True:
        command = recognize_speech()
        if "起動" in command:
            speak_text("Spotifyを起動します。")
            open_spotify_web_app()
            device_id = choose_device()
            if device_id:
                search_and_play(device_id)
                # 音楽再生後の案内はテキストのみ
                print("再生コントロールを操作するにはコマンドを入力してください。停止、再開、次、前、再生コントロール終了など。終了するには終了と言ってください。")
                playback_controls()

            while True:
                speak_text("再生コントロールを終了しますか？ '再生コントロール終了' と言ってください。再開するには '起動' と言ってください。")
                command = recognize_speech()
                if "終了" in command:
                    speak_text("プログラムを終了します。")
                    # すべてのウィンドウからタイトルを検索
                    for window in gw.getAllTitles():
                        if window_title in window:
                            target_window = gw.getWindowsWithTitle(window)[0]
                            break

                    if target_window:
                        # 対象のウィンドウをアクティブにする
                        target_window.activate()
                        time.sleep(0.5)  # アクティブ化が完了するまで少し待つ
                        sys.exit()  # プログラムを終了
                elif "再生コントロール終了" in command:
                    speak_text("再生コントロールを終了します。")
                    break  # 再生コントロールを終了
                elif "起動" in command:
                    playback_controls()  # 再度再生コントロールを開始
                    break  # 再度再生コントロールを開始

if __name__ == "__main__":
    main()
