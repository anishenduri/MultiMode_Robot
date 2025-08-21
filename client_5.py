import socket
import cv2
import mediapipe as mp
import tkinter as tk
from tkinter import scrolledtext
import threading
import speech_recognition as sr
import google.generativeai as genai
import pyttsx3
import sounddevice as sd
from fuzzywuzzy import process

# ===== CONFIG =====
EV3_IP = "169.254.60.46"  # Your EV3 IP
PORT = 9999
GEMINI_API_KEY = ""
GEMINI_MODEL_ID = "gemini-1.5-pro-latest"

ROBOT_COMMANDS = [
    "forward", "backward", "left", "right",
    "open", "close", "distance", "color",
    "angle", "stop", "history", "exit"
]

# ===== GEMINI INIT =====
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL_ID)

# ===== TTS Setup =====
def speak_output(text):
    try:
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            if "Mivi Play" in dev['name'] and dev['max_output_channels'] > 0:
                sd.default.device = idx
                break
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print("TTS Error:", e)

# ===== FUNCTIONS =====
def get_gemini_reply(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        output_box.insert(tk.END, "Gemini Error: {}\n".format(e))
        output_box.see(tk.END)
        return "Sorry, I couldn't process your request."

def interpret_command(reply):
    best_match, score = process.extractOne(reply.lower(), ROBOT_COMMANDS)
    if score >= 70:  # Confidence threshold
        return best_match
    return None

# ===== CONNECT TO EV3 =====
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((EV3_IP, PORT))

# ===== UI Setup =====
root = tk.Tk()
root.title("Multi-Mode Control Robot")
root.configure(bg="#2E2E2E")

# Output display
output_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=15, bg="#1E1E1E", fg="white")
output_box.pack(padx=10, pady=10)

# Button Frame
button_frame = tk.Frame(root, bg="#2E2E2E")
button_frame.pack(pady=10)

def send_command(cmd):
    try:
        sock.sendall(cmd.encode())
        response = sock.recv(1024).decode()
        output_box.insert(tk.END, "EV3: " + response + "\n")
        output_box.see(tk.END)
        if response and "Unknown command" not in response:
            speak_output(response)
        return response
    except Exception as e:
        output_box.insert(tk.END, "Error: " + str(e) + "\n")
        return ""

def make_button(text, cmd, color):
    return tk.Button(button_frame, text=text, command=lambda: send_command(cmd),
                     width=12, height=2, bg=color, fg="white")

# Row 1
make_button("Forward", "forward", "#228B22").grid(row=0, column=0, padx=5, pady=5)
make_button("Backward", "backward", "#FF4500").grid(row=0, column=1, padx=5, pady=5)
make_button("Left", "left", "#1E90FF").grid(row=0, column=2, padx=5, pady=5)

# Row 2
make_button("Right", "right", "#FFD700").grid(row=1, column=0, padx=5, pady=5)
make_button("Open Claw", "open", "#8B008B").grid(row=1, column=1, padx=5, pady=5)
make_button("Close Claw", "close", "#A0522D").grid(row=1, column=2, padx=5, pady=5)

# Row 3
make_button("Distance", "distance", "#FF69B4").grid(row=2, column=0, padx=5, pady=5)
make_button("Color", "color", "#20B2AA").grid(row=2, column=1, padx=5, pady=5)
make_button("Angle", "angle", "#708090").grid(row=2, column=2, padx=5, pady=5)

# ==== Q&A Entry ====
qa_frame = tk.Frame(root, bg="#2E2E2E")
qa_frame.pack(pady=10)
qa_label = tk.Label(qa_frame, text="Q&A :", fg="white", bg="#2E2E2E")
qa_label.grid(row=0, column=0, padx=5)
qa_entry = tk.Entry(qa_frame, width=40)
qa_entry.grid(row=0, column=1, padx=5)

def qa_control():
    question = qa_entry.get().strip()
    qa_entry.delete(0, tk.END)
    if question:
        reply = get_gemini_reply(question)
        output_box.insert(tk.END, "Robot: " + reply + "\n")
        speak_output(reply)

tk.Button(qa_frame, text="Ask", command=qa_control, bg="#4B0082", fg="white").grid(row=0, column=2, padx=5)

# ==== Voice Control ====
recognizer = sr.Recognizer()
def voice_control():
    with sr.Microphone() as source:
        output_box.insert(tk.END, "Listening...\n")
        output_box.see(tk.END)
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio)
        output_box.insert(tk.END, "You said: " + text + "\n")
        command = interpret_command(text)
        if command:
            send_command(command)
        else:
            reply = get_gemini_reply(text)
            output_box.insert(tk.END, "Robot: " + reply + "\n")
            speak_output(reply)
    except Exception as e:
        output_box.insert(tk.END, "Voice Error: " + str(e) + "\n")

tk.Button(root, text="🎤 Voice Control", command=lambda: threading.Thread(target=voice_control).start(),
          bg="#006400", fg="white").pack(pady=5)

# ==== Gesture Control ====
def gesture_control():
    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils
    hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
    cap = cv2.VideoCapture(0)
    output_box.insert(tk.END, "Gesture control active. Press 'q' to quit.\n")
    while True:
        success, img = cap.read()
        if not success:
            break
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                index_tip = hand_landmarks.landmark[8]
                thumb_tip = hand_landmarks.landmark[4]
                distance = abs(index_tip.x - thumb_tip.x) + abs(index_tip.y - thumb_tip.y)
                if distance > 0.15:
                    send_command("open")
                else:
                    send_command("close")
        cv2.imshow("Gesture Control", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

tk.Button(root, text="✋ Gesture Control", command=lambda: threading.Thread(target=gesture_control).start(),
          bg="#8B4513", fg="white").pack(pady=5)

# Exit Button
tk.Button(root, text="Exit", command=lambda: (sock.close(), root.destroy()), bg="#B22222", fg="white").pack(pady=5)

root.mainloop()
