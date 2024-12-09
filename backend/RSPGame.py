import cv2
import mediapipe as mp
import random
import math
import time

# MediaPipeの手のジェスチャー認識用の設定
mp_hands = mp.solutions.hands
hands = mp_hands.Hands()

# じゃんけんの手の形を定義
gesture_map = {
    "rock": "グー",
    "scissors": "チョキ",
    "paper": "パー"
}

def calculate_angle(a, b, c):
    """
    3つのランドマーク座標から角度を計算
    """
    # a, b, c はランドマークの座標
    ab = [b[0] - a[0], b[1] - a[1]]  # ベクトルAB
    bc = [c[0] - b[0], c[1] - b[1]]  # ベクトルBC
    dot_product = ab[0] * bc[0] + ab[1] * bc[1]  # 内積
    magnitude_ab = math.sqrt(ab[0]**2 + ab[1]**2)  # ベクトルABの大きさ
    magnitude_bc = math.sqrt(bc[0]**2 + bc[1]**2)  # ベクトルBCの大きさ
    cos_angle = dot_product / (magnitude_ab * magnitude_bc)
    angle = math.acos(cos_angle) * 180 / math.pi  # ラジアンから度数法に変換
    return angle

def recognize_hand_gesture(hand_landmarks):
    if hand_landmarks is None:
        return None

    # 必要なランドマークを取得
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]

    # 各指の先端と手首との距離を計算
    def distance(point1, point2):
        return math.sqrt((point1.x - point2.x)**2 + (point1.y - point2.y)**2)

    thumb_dist = distance(thumb_tip, wrist)
    index_dist = distance(index_tip, wrist)
    middle_dist = distance(middle_tip, wrist)
    ring_dist = distance(ring_tip, wrist)
    pinky_dist = distance(pinky_tip, wrist)

    # 基準値を設定（調整が必要）
    threshold = 0.38  # 距離がこの値以上なら「開いている」と判断

    # 指が開いているかの判定
    is_thumb_open = thumb_dist > threshold
    is_index_open = index_dist > threshold
    is_middle_open = middle_dist > threshold
    is_ring_open = ring_dist > threshold
    is_pinky_open = pinky_dist > threshold

    # ジェスチャーの判定
    if not is_thumb_open and not is_index_open and not is_middle_open and not is_ring_open and not is_pinky_open:
        return "rock"  # グー
    elif is_thumb_open and is_index_open and is_middle_open and is_ring_open and is_pinky_open:
        return "paper"  # パー
    else:
        return "scissors"  # チョキ

def play_rock_paper_scissors(player_choice):
    """
    じゃんけんをAIとプレイ
    """
    ai_choice = random.choice(["rock", "scissors", "paper"])
    print(f"あなたの選択: {gesture_map[player_choice]}")
    print(f"AIの選択: {gesture_map[ai_choice]}")

    if player_choice == ai_choice:
        return "draw", "引き分け"
    elif (player_choice == "rock" and ai_choice == "scissors") or \
         (player_choice == "scissors" and ai_choice == "paper") or \
         (player_choice == "paper" and ai_choice == "rock"):
        return "player", "あなたの勝ち！"
    else:
        return "ai", "AIの勝ち！"

# Webカメラをキャプチャする
cap = cv2.VideoCapture(0)

# 前回認識した手のジェスチャーを保存
previous_gesture = None

countdown_started = False
countdown_start_time = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # BGRからRGBに変換
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # 手のジェスチャーを認識
    results = hands.process(frame_rgb)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # 手のジェスチャーを認識
            gesture = recognize_hand_gesture(hand_landmarks)
            
            if gesture and gesture != previous_gesture:
                print(f"認識されたジェスチャー: {gesture_map[gesture]}")
                
                # カウントダウン開始
                countdown_started = True
                countdown_start_time = time.time()
                previous_gesture = gesture

            # ランドマークを描画
            mp.solutions.drawing_utils.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    # カウントダウン処理
    if countdown_started:
        elapsed_time = time.time() - countdown_start_time
        countdown = 5 - int(elapsed_time)
        if countdown > 0:
            cv2.putText(frame, f"カウントダウン: {countdown}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        else:
            # カウントダウン終了、じゃんけん結果を表示
            if previous_gesture is not None:
                winner, result_message = play_rock_paper_scissors(previous_gesture)
                print(result_message)
                cv2.putText(frame, f"結果: {result_message}", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                if winner != "draw":
                    cv2.imshow('Rock Paper Scissors', frame)
                    time.sleep(3)
                break  # 勝敗が決まったら終了

                countdown_started = False  # カウントダウン終了

    # 画面に表示
    cv2.imshow('Rock Paper Scissors', frame)

    # 'q'を押すと手動で終了
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 後片付け
cap.release()
cv2.destroyAllWindows()