import json, time, os
import speech_recognition as sr
from gtts import gTTS
from pygame import mixer
from awscrt import mqtt
from awsiot import mqtt_connection_builder

#各デバイスごとに設定(AWS IoT → セキュリティ → ポリシー 編集 → JSON → 保存&activate)
client_id = ""

def get_recognition(listener):
    try:
        with sr.Microphone() as source:
            print("聞き取り中...")
            listener.adjust_for_ambient_noise(source)
            voice = listener.listen(source, timeout=10, phrase_time_limit=5)
            voice_text = listener.recognize_google(voice, language="ja-JP")
            return voice_text
    except KeyboardInterrupt:
        return -1
    except:
        return None
    #message = input("音声入力：")
    #if message == "-1":
    #    return -1
    #else:
    #    return message

def speaking(text):
    tts1 = gTTS(text=text, lang='ja')
    tts1.save('.mp3')

    mixer.init()
    mixer.music.load('.mp3')
    mixer.music.play()
    while mixer.music.get_busy():
        time.sleep(0.1)
    mixer.music.unload()
    os.remove('.mp3')

def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    global client_id, state
    message = json.loads(payload)
    if message.get("client_id") != client_id:
        print(f"受信：{message.get('message')}")
        speaking(message.get('message'))
        state = "開始"

def ai_chat():
    global client_id, state
    # 接続の確立
    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint="xxxx-xxx-xxx.xom",
        port=xxxx,
        cert_filepath="xxxx-xxx.cert.pem",
        pri_key_filepath="xxxx-xxx.private.key",
        ca_filepath="xxxx.crt",
        client_id=client_id,
        clean_session=False,
        keep_alive_secs=30,
        )

    try:
        connect_future = mqtt_connection.connect()
        connect_future.result()
        print("Connected")
    except Exception as e:
        print(f"Connection failed: {e}")
        exit(1)

    # トピックの登録
    subscribe_future, packet_id = mqtt_connection.subscribe(
        topic="",
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=on_message_received
    )
    subscribe_future.result()

    listener = sr.Recognizer()

    try:
        state = "停止"
        command = ["開始", "終了", "停止", "音声再生"]
        repeat = False
        while True:
            if state != command[3]:
                message = get_recognition(listener)
            else:
                if repeat == False:
                    print("音声再生中")
                    repeat = True
            if message in command:
                state = message

            if state == command[1] or message == -1:
                print("終了")
                break

            if state == command[2] and repeat == False:
                print("停止中")
                repeat = True
                continue

            if state == command[0]:
                if message and message != "開始":
                    print(f"送信:{message}")
                    state = "音声再生"
                    # メッセージ送信
                    mqtt_connection.publish(
                        topic="",
                        payload=json.dumps({"client_id": client_id, "message": message}),
                        qos=mqtt.QoS.AT_LEAST_ONCE
                    )
                else:
                    repeat = False
                    print("待機中")

    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        # 切断
        disconnect_future = mqtt_connection.disconnect()
        disconnect_future.result()
        print("Disconnected!")

if __name__ == '__main__':
    ai_chat()