import json, time
import threading
from awscrt import mqtt
from awsiot import mqtt_connection_builder
from dotenv import load_dotenv
import os
import openai

# 環境変数をロード
load_dotenv()

#各デバイスごとに設定(AWS IoT → セキュリティ → ポリシー 編集 → JSON → 保存&activate)
client_id = ""
openai.api_key = os.getenv("OPENAI_API_KEY")

messages = [
    {"role": "system", "content": "あなたは親切なAIアシスタントです。"},
    ]

def chatgpt(messages):
    completion = openai.ChatCompletion.create(
        model="",
        messages=messages,
        temperature=0.7
    )
    response = completion.choices[0].message.content
    messages.append({"role": "assistant", "content": response})
    return response

def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    global client_id, mqtt_connection
    message = json.loads(payload)

    if message.get("client_id") != client_id:
        print(f"受信：{message.get('message')}")
        messages.append({"role": "user", "content": message.get("message")})
        response = chatgpt(messages)
        mqtt_connection.publish(
                        topic="",
                        payload=json.dumps({"client_id": client_id, "message": response}),
                        qos=mqtt.QoS.AT_LEAST_ONCE
        )


def ai_chat():
    global client_id, mqtt_connection
    # 接続の確立
    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint="xxxx-xxxx-xx.com",
        port=xxxx,
        cert_filepath="xxx.pem",
        pri_key_filepath="xxxx.private.key",
        ca_filepath="xxx.crt",
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

    received_all_event = threading.Event()

    # トピックの登録
    subscribe_future, packet_id = mqtt_connection.subscribe(
        topic="",
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=on_message_received
    )
    subscribe_future.result()

    received_all_event.wait()

    # 切断
    disconnect_future = mqtt_connection.disconnect()
    disconnect_future.result()
    print("Disconnected!")

if __name__ == '__main__':
    ai_chat()