import requests
from datetime import datetime, timedelta
import speech_recognition as sr  # 音声認識用ライブラリ
import pyttsx3  # 音声読み上げ用ライブラリ
import re  # 自然言語処理用（簡単なテキスト解析）

# OpenWeatherMap API設定
API_KEY = ""  # 取得したAPIキーを入力
BASE_URL = ""  # 天気予報のエンドポイント
UNIT = "metric"  # 摂氏表示 ("imperial" に変更すると華氏)

# 都道府県名リスト
PREFECTURE_LIST = [
    "北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", 
    "神奈川", "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", 
    "大阪", "兵庫", "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", 
    "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"
]

# 都道府県名 + 市町村名を自動認識する
def get_prefecture_and_city(input_text):
    # 都道府県を探す
    prefecture = None
    for pref in PREFECTURE_LIST:
        if pref in input_text:
            prefecture = pref
            break

    # 市町村名（都道府県内の具体的な地域）を認識するため、入力されたテキストに市町村名が含まれているか
    city_match = re.search(r"(郡山|札幌|名古屋|大阪|福岡|東京|京都|横浜|神戸|広島|仙台)", input_text)
    city = city_match.group(0) if city_match else None

    return prefecture, city

# 天気データを取得
def get_weather_forecast(city):
    city_translation = {
        "大阪": "Osaka",
        "東京": "Tokyo",
        "名古屋": "Nagoya",
        "京都": "Kyoto",
        "横浜": "Yokohama"
    }
    city = city_translation.get(city, city)

    params = {
        "q": f"{city},JP",
        "appid": API_KEY,
        "units": UNIT,
        "lang": "ja"
    }
    print("APIリクエストパラメータ:", params)
    response = requests.get(BASE_URL, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"APIリクエストに失敗しました: {response.status_code}")
        print("エラー詳細:", response.json())
        return None

# 指定した日付の天気情報を取得
def get_weather(data, date_str):
    if not data:
        return None

    forecast_list = data.get("list", [])
    weather = [entry for entry in forecast_list if date_str in entry["dt_txt"]]

    if weather:
        return weather
    else:
        print(f"{date_str} の天気情報が見つかりませんでした。")
        return None

# 日付をフォーマットして「年」を省略
def format_date_without_year(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%m月%d日")

# 音声認識でテキストを取得
def recognize_audio():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        instruction = "天気を知りたい場所と日付を音声で教えてください。例: 明日の大阪の天気を教えてください。"
        print(instruction)
        speak(instruction)
        recognizer.adjust_for_ambient_noise(source)
        print("録音を開始します。")
        audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)  # ここで音声認識時間を調整
        try:
            text = recognizer.recognize_google(audio, language='ja-JP')
            print(f"認識されたテキスト: {text}")
            return text
        except sr.UnknownValueError:
            error_message = "音声を認識できませんでした。"
            print(error_message)
            speak(error_message)
            return None
        except sr.RequestError as e:
            error_message = f"音声認識サービスのエラー: {e}"
            print(error_message)
            speak(error_message)
            return None

# 音声で読み上げる
def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 1)
    engine.say(text)
    engine.runAndWait()

# 入力テキストから日付と場所を抽出
def extract_date_and_location(input_text):
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    target_date = None

    # 日付を解析
    if "今日" in input_text:
        target_date = today.strftime("%Y-%m-%d")
    elif "明日" in input_text:
        target_date = tomorrow.strftime("%Y-%m-%d")

    # 都道府県と市町村を解析
    prefecture, city = get_prefecture_and_city(input_text)

    return target_date, prefecture, city

# メイン処理
def main():
    input_text = recognize_audio()
    if input_text:
        target_date, prefecture, city = extract_date_and_location(input_text)

        if target_date and prefecture:
            if city is None:
                print("市町村が見つかりませんでした。代表都市を使用します。")
                city = prefecture  # 市町村が見つからない場合、都道府県名を代用する

            print(f"場所: {prefecture}, 市町村: {city}, 日付: {target_date}")

            weather_data = get_weather_forecast(city)
            weather_info = get_weather(weather_data, target_date)

            if weather_info:
                formatted_date = format_date_without_year(target_date)
                weather_summary = f"{formatted_date}の{prefecture} ({city})の天気:\n"
                for forecast in weather_info:
                    time = forecast["dt_txt"][11:16]
                    temp = forecast["main"]["temp"]
                    weather = forecast["weather"][0]["description"]
                    weather_summary += f"- {time}: 温度 {temp}°, 天気: {weather}\n"
                print(weather_summary)
                speak(weather_summary)
            else:
                error_message = "天気データが取得できませんでした。"
                print(error_message)
                speak(error_message)
        else:
            error_message = "場所または日付が認識できませんでした。"
            print(error_message)
            speak(error_message)

if __name__ == "__main__":
    main()
