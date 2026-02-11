# ---------- IMPORTS ----------
import speech_recognition as sr
import pyttsx3
import requests
import re
import os
import webbrowser
import sys
import threading

from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# ---------- WINDOWS UTF-8 ----------
sys.stdout.reconfigure(encoding="utf-8")

# ---------- CONFIG ----------
# API key is now read ONLY from environment variable
API_KEY = os.getenv("OPENROUTER_API_KEY")

API_URL = "https://openrouter.ai/api/v1/chat/completions"

if not API_KEY:
    print("ERROR: Missing OpenRouter API key. Set OPENROUTER_API_KEY environment variable.")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://localhost",
    "X-Title": "Jarvis Assistant"
}

# ---------- SPEECH RECOGNITION ----------
recognizer = sr.Recognizer()
microphone = sr.Microphone()

# ---------- GLOBALS FOR STOP FEATURE ----------
current_engine = None
engine_lock = threading.Lock()

# ---------- TEXT TO SPEECH (NON-BLOCKING) ----------
def speak(text):
    global current_engine
    if not text:
        return

    def _speak():
        global current_engine
        try:
            engine = pyttsx3.init("sapi5")
            voices = engine.getProperty("voices")
            engine.setProperty("voice", voices[0].id)
            engine.setProperty("rate", 180)

            with engine_lock:
                current_engine = engine

            engine.say(text)
            engine.runAndWait()

        except Exception as e:
            print("TTS error:", e)

        finally:
            with engine_lock:
                current_engine = None

    threading.Thread(target=_speak, daemon=True).start()

# ---------- STOP SPEAKING ----------
def stop_speaking():
    global current_engine
    with engine_lock:
        if current_engine:
            current_engine.stop()

# ---------- LISTEN ----------
def listen():
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("Listening...")
            audio = recognizer.listen(source)

        print("Recognizing...")
        text = recognizer.recognize_google(audio)
        print("You said:", text)
        return text

    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print("Speech error:", e)
        return None

# ---------- CLEAN AI RESPONSE ----------
def clean_response(text):
    if not text:
        return None

    text = re.sub(
        r"[\U0001F600-\U0001F64F"
        r"\U0001F300-\U0001F5FF"
        r"\U0001F680-\U0001F6FF"
        r"\U0001F1E0-\U0001F1FF]+",
        "",
        text
    )

    text = re.sub(r"[*_#>`~\-]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()

# ---------- AI CHAT ----------
def chat_with_ai(prompt):
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "You are Jarvis, a helpful voice assistant. Respond clearly without emojis or symbols."
            },
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=20)

        if response.status_code != 200:
            return "Sorry, I could not reach the AI."

        reply = response.json()["choices"][0]["message"]["content"]
        clean_text = clean_response(reply)
        print("AI:", clean_text)
        return clean_text

    except Exception as e:
        print("AI error:", e)
        return "Something went wrong."

# ---------- WAKE WORD ----------
def is_wake_word(command):
    if not command:
        return False
    return command.lower().startswith("jarvis")

# ---------- VOLUME CONTROL ----------
def set_volume(action):
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_,
        CLSCTX_ALL,
        None
    )
    volume = cast(interface, POINTER(IAudioEndpointVolume))

    current = volume.GetMasterVolumeLevelScalar()

    if action == "up":
        volume.SetMasterVolumeLevelScalar(min(current + 0.1, 1.0), None)
        speak("Volume increased")

    elif action == "down":
        volume.SetMasterVolumeLevelScalar(max(current - 0.1, 0.0), None)
        speak("Volume decreased")

    elif action == "mute":
        volume.SetMute(1, None)
        speak("Volume muted")

    elif action == "unmute":
        volume.SetMute(0, None)
        speak("Volume unmuted")

# ---------- COMMAND HANDLER ----------
def handle_command(command):
    if not is_wake_word(command):
        return

    command = command.lower().replace("jarvis", "", 1).strip()
    cmd = command

    if "stop" in cmd:
        stop_speaking()
        return

    if "open chrome" in cmd:
        stop_speaking()
        speak("Opening Chrome")
        webbrowser.open("https://google.com")
        return

    if "exit" in cmd or "quit" in cmd or "bye" in cmd:
        stop_speaking()
        speak("Goodbye")
        sys.exit(0)

    response = chat_with_ai(command)
    speak(response)

# ---------- MAIN ----------
if __name__ == "__main__":
    speak("Hello, I am Jarvis. I am ready.")

    while True:
        command = listen()
        if command:
            handle_command(command)
