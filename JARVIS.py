import speech_recognition as sr
import pyttsx3
import requests
import re
import os
import webbrowser
import sys
import threading
import ctypes

from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

sys.stdout.reconfigure(encoding="utf-8")

API_KEY = "ur api key"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

recognizer = sr.Recognizer()
microphone = sr.Microphone()

current_engine = None
engine_lock = threading.Lock()

chat_history = []

# ---------- SPEAK ----------
def speak(text):
    global current_engine

    def _run():
        global current_engine
        engine = pyttsx3.init("sapi5")
        engine.setProperty("rate", 180)

        with engine_lock:
            current_engine = engine

        engine.say(text)
        engine.runAndWait()

        with engine_lock:
            current_engine = None

    threading.Thread(target=_run, daemon=True).start()


def stop_speaking():
    global current_engine
    with engine_lock:
        if current_engine:
            current_engine.stop()


# ---------- LISTEN ----------
def listen():
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, 0.5)
            print("Listening...")
            audio = recognizer.listen(source)

        text = recognizer.recognize_google(audio)
        print("You:", text)
        return text.lower()

    except:
        return None


# ---------- CLEAN ----------
def clean_response(text):
    text = re.sub(r"[^\x00-\x7F]+", "", text)
    return text.strip()


# ---------- AI ----------
def chat_with_ai(prompt):
    global chat_history

    messages = [
        {
            "role": "system",
            "content": """
You are Jarvis.

STRICT RULE:
If user wants system control, reply ONLY:

ACTION: <action>
VALUE: <value>

No extra words.

Actions:
open_website
search_google
open_app
volume_up (increase, louder)
volume_down (decrease, lower)
mute
unmute
shutdown
restart
"""
        }
    ] + chat_history + [{"role": "user", "content": prompt}]

    payload = {
        "model": "meta-llama/llama-3-70b-instruct",
        "messages": messages
    }

    try:
        res = requests.post(API_URL, headers=HEADERS, json=payload)
        reply = res.json()["choices"][0]["message"]["content"]

        print("AI RAW RESPONSE:", reply)

        chat_history.append({"role": "user", "content": prompt})
        chat_history.append({"role": "assistant", "content": reply})
        chat_history = chat_history[-6:]

        return clean_response(reply)

    except Exception as e:
        print("AI error:", e)
        return "Error connecting to AI"


# ---------- PARSER ----------
def parse_ai_action(text):
    if not text:
        return None, None

    text_lower = text.lower()

    if "volume_up" in text_lower or "increase volume" in text_lower or "louder" in text_lower:
        return "VOLUME_UP", None

    if "volume_down" in text_lower or "decrease volume" in text_lower or "lower" in text_lower:
        return "VOLUME_DOWN", None

    if "mute" in text_lower and "unmute" not in text_lower:
        return "MUTE", None

    if "unmute" in text_lower:
        return "UNMUTE", None

    if "shutdown" in text_lower:
        return "SHUTDOWN", None

    if "restart" in text_lower:
        return "RESTART", None

    if "ACTION:" in text:
        try:
            action = text.split("ACTION:")[1].split("\n")[0].strip().upper()
            value = None
            if "VALUE:" in text:
                value = text.split("VALUE:")[1].split("\n")[0].strip()
            return action, value
        except:
            pass

    return None, None


# ---------- VOLUME (FINAL FIX - NO PYCAW) ----------
def set_volume(action):
    try:
        VK_VOLUME_UP = 0xAF
        VK_VOLUME_DOWN = 0xAE
        VK_VOLUME_MUTE = 0xAD

        if action == "up":
            for _ in range(5):
                ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
            speak("Volume increased")

        elif action == "down":
            for _ in range(5):
                ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
            speak("Volume decreased")

        elif action == "mute":
            ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
            speak("Muted")

        elif action == "unmute":
            ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
            speak("Unmuted")

    except Exception as e:
        print("Volume error:", e)
        speak("Volume control failed")


# ---------- EXECUTE ----------
def execute_action(action, value):
    if action == "OPEN_WEBSITE":
        webbrowser.open(value)
        speak("Opening")

    elif action == "SEARCH_GOOGLE":
        webbrowser.open(f"https://www.google.com/search?q={value}")
        speak("Searching")

    elif action == "OPEN_APP":
        os.system(f"start {value}")
        speak("Opening app")

    elif action == "VOLUME_UP":
        set_volume("up")

    elif action == "VOLUME_DOWN":
        set_volume("down")

    elif action == "MUTE":
        set_volume("mute")

    elif action == "UNMUTE":
        set_volume("unmute")

    elif action == "SHUTDOWN":
        speak("Shutting down")
        os.system("shutdown /s /t 5")

    elif action == "RESTART":
        speak("Restarting")
        os.system("shutdown /r /t 5")

    else:
        speak("I don't understand")


# ---------- MAIN ----------
def handle_command(command):
    if not command:
        return

    if "jarvis" in command:
        command = command.replace("jarvis", "").strip()

    if "stop" in command:
        stop_speaking()
        return

    response = chat_with_ai(command)

    action, value = parse_ai_action(response)

    if action:
        execute_action(action, value)
    else:
        speak(response)


# ---------- RUN ----------
if __name__ == "__main__":
    speak("Hello, how can I help you?")

    while True:
        cmd = listen()
        if cmd:
            handle_command(cmd)
