import cv2 
import mediapipe as mp 
import threading 
import asyncio 
from io import BytesIO 
import edge_tts 
import pygame 
import queue 
import time 
import sys 

pygame.mixer.init() 

is_running = True 

last_spoken_gesture = "No Hand" 

current_detected_gesture = "No Hand" 
gesture_start_time = 0 

STABILITY_DELAY = 1.0 

SPEECH_SPEED = "+25%" 
VOICE_MODEL = "en-US-AndrewNeural"

speech_queue = queue.Queue() 

def speech_worker():

    global is_running 
    
    loop = asyncio.new_event_loop() 
    asyncio.set_event_loop(loop) 
    
    async def play_audio(gesture_text): 
        try: 
            communicate = edge_tts.Communicate(gesture_text, VOICE_MODEL, rate=SPEECH_SPEED) 
            audio_buffer = BytesIO() 
            async for chunk in communicate.stream(): 
                if not is_running:
                    return 
                if chunk["type"] == "audio": 
                    audio_buffer.write(chunk["data"]) 
                    
            audio_buffer.seek(0) 
            if is_running: 
                pygame.mixer.music.load(audio_buffer, 'mp3') 
                pygame.mixer.music.play() 
                
                while pygame.mixer.music.get_busy() and is_running: 
                    await asyncio.sleep(0.05) 
        except Exception: 
            pass 

    while is_running: 
        try: 
            gesture_text = speech_queue.get(timeout=0.2) 
        except queue.Empty: 
            continue 
            
        if not is_running: 
            speech_queue.task_done() 
            break 
                
        loop.run_until_complete(play_audio(gesture_text)) 
        speech_queue.task_done() 
        
    loop.close() 

worker_thread = threading.Thread(target=speech_worker, daemon=True) 
worker_thread.start() 

def speak(text): 
     
    if is_running: 
        speech_queue.put(text) 

mp_hands = mp.solutions.hands 
mp_draw = mp.solutions.drawing_utils 
hands = mp_hands.Hands( 
    max_num_hands=1, 
    min_detection_confidence=0.7, 
    min_tracking_confidence=0.7 
) 

cap = cv2.VideoCapture(0) 
tip_ids = [4, 8, 12, 16, 20]

while is_running: 
    success, frame = cap.read() 
    if not success: 
        break 
        
    frame = cv2.flip(frame, 1) 
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) 
    results = hands.process(rgb) 
    gesture = "No Hand" 
    finger_status = ["DOWN"] * 5 
    
    if results.multi_hand_landmarks: 
        hand = results.multi_hand_landmarks[0]
        mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS) 
        landmarks = hand.landmark 
        finger_status = [] 
        
        if landmarks[4].x < landmarks[3].x:
            finger_status.append("UP") 
        else: 
            finger_status.append("DOWN") 
            
        for tip in tip_ids[1:]: 
            if landmarks[tip].y < landmarks[tip - 2].y: 
                finger_status.append("UP") 
            else: 
                finger_status.append("DOWN") 
                
        if finger_status == ["UP", "UP", "UP", "UP", "UP"]: 
            gesture = "HELLO" 
        elif finger_status == ["DOWN", "DOWN", "DOWN", "DOWN", "DOWN"]: 
            gesture = "STOP" 
        elif finger_status == ["DOWN", "UP", "DOWN", "DOWN", "DOWN"]: 
            gesture = "ONE" 
        elif finger_status == ["DOWN", "UP", "UP", "DOWN", "DOWN"]: 
            gesture = "PEACE" 
        elif finger_status == ["DOWN", "UP", "UP", "UP", "DOWN"]: 
            gesture = "THREE" 
        elif finger_status == ["DOWN", "UP", "UP", "UP", "UP"]: 
            gesture = "FOUR" 
        elif finger_status == ["UP", "DOWN", "DOWN", "DOWN", "DOWN"]: 
            gesture = "GOOD" 
        elif finger_status == ["UP", "UP", "DOWN", "DOWN", "UP"]: 
            gesture = "I LOVE YOU" 
        elif finger_status == ["UP", "DOWN", "DOWN", "DOWN", "UP"]: 
            gesture = "CALL ME" 
        elif finger_status == ["DOWN", "UP", "DOWN", "DOWN", "UP"]: 
            gesture = "ROCK" 
        elif finger_status == ["UP", "UP", "DOWN", "DOWN", "DOWN"]: 
            gesture = "GUN" 
        elif finger_status == ["DOWN", "DOWN", "UP", "UP", "UP"]: 
            gesture = "OK"
        elif finger_status == ["UP", "UP", "UP", "DOWN", "DOWN"]: 
            gesture = "EIGHT"
        elif finger_status == ["UP", "DOWN", "UP", "UP", "UP"]: 
            gesture = "NINE"  
        else: 
            gesture = "UNKNOWN" 

    names = ["Thumb", "Index", "Middle", "Ring", "Pinky"] 
    y = 80 
    for i in range(5): 
        cv2.putText(frame, f"{names[i]} : {finger_status[i]}", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y += 30 

    if gesture != current_detected_gesture: 
        current_detected_gesture = gesture 
        gesture_start_time = time.time() 
    else: 
        if gesture not in ["No Hand", "UNKNOWN"] and gesture != last_spoken_gesture: 
            elapsed_time = time.time() - gesture_start_time 
            time_left = max(0.0, STABILITY_DELAY - elapsed_time) 
            
            if time_left > 0: 
                cv2.putText(frame, f"Holding... {time_left:.1f}s", (280, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2) 
                
            if elapsed_time >= STABILITY_DELAY: 
                speak(gesture) 
                last_spoken_gesture = gesture 

    if gesture in ["No Hand", "UNKNOWN"]: 
        last_spoken_gesture = "No Hand" 

    cv2.rectangle(frame, (0, 0), (500, 60), (0, 0, 0), -1) 
    cv2.putText(frame, "Gesture : " + gesture, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2) 
    
    cv2.imshow("Gesture Recognition", frame) 

    if cv2.waitKey(1) & 0xFF == 27: 
        is_running = False 
        break 

cap.release() 
hands.close() 
pygame.mixer.music.stop() 
pygame.mixer.quit() 
cv2.destroyAllWindows() 

sys.exit(0)
