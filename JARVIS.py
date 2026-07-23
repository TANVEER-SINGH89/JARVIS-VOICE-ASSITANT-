import speech_recognition as sr
import pyttsx3
import requests
import re
import os
import webbrowser
import sys
import threading
import ctypes

sys.stdout.reconfigure(encoding="utf-8")

API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not API_KEY or API_KEY == "ur api key":
    print("Warning: OPENROUTER_API_KEY environment variable not set. Secure credential handling is required. AI features will not function correctly without this key.")

API_URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY if API_KEY else ''}",
    "Content-Type": "application/json",
}

recognizer = sr.Recognizer()
microphone = None
try:
    microphone = sr.Microphone()
except Exception as e:
    print("Warning: Microphone not available, voice input disabled.", e)

current_engine = None
engine_lock = threading.Lock()

chat_history = []

# ---------- SPEAK ----------
def speak(text):
    global current_engine
    print(f"JARVIS: {text}")

    def _run():
        global current_engine
        try:
            # First try default engine, then try specific drivers if it fails
            try:
                engine = pyttsx3.init()
            except Exception:
                try:
                    engine = pyttsx3.init("sapi5")
                except Exception:
                    try:
                        engine = pyttsx3.init("espeak")
                    except Exception:
                        # Fallback to gTTS if pyttsx3 fails completely
                        from gtts import gTTS
                        import tempfile
                        import subprocess
                        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                            temp_filename = f.name
                        tts = gTTS(text=text, lang="en")
                        tts.save(temp_filename)
                        # Attempt to play the sound using platform-specific players
                        if sys.platform == "win32":
                            os.system(f'start {temp_filename}')
                        elif sys.platform == "darwin":
                            subprocess.run(["afplay", temp_filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        else:
                            # Linux fallback
                            subprocess.run(["play", temp_filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        try:
                            os.unlink(temp_filename)
                        except Exception:
                            pass
                        return

            engine.setProperty("rate", 180)

            with engine_lock:
                current_engine = engine

            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            # Fail silently on audio issues, as text has already been printed
            pass
        finally:
            with engine_lock:
                current_engine = None

    threading.Thread(target=_run, daemon=True).start()


def stop_speaking():
    global current_engine
    with engine_lock:
        if current_engine:
            try:
                current_engine.stop()
            except Exception:
                pass


# ---------- LISTEN ----------
def listen():
    global microphone
    if microphone is None:
        try:
            user_input = input("You (text mode): ")
            return user_input.strip().lower() if user_input else None
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            sys.exit(0)
        except Exception:
            return None

    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, 0.5)
            print("Listening...")
            audio = recognizer.listen(source)

        text = recognizer.recognize_google(audio)
        print("You:", text)
        return text.lower()

    except Exception:
        # Fallback to text input if voice listening fails
        try:
            print("Microphone listening failed. Falling back to text mode.")
            user_input = input("You (text mode): ")
            return user_input.strip().lower() if user_input else None
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            sys.exit(0)
        except Exception:
            return None


# ---------- CLEAN ----------
def clean_response(text):
    text = re.sub(r"[^\x00-\x7F]+", "", text)
    return text.strip()


# ---------- AI ----------
def chat_with_ai(prompt):
    global chat_history

    if not API_KEY or API_KEY == "ur api key":
        return "Please set the OPENROUTER_API_KEY environment variable to use JARVIS."

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

    # First, try to extract structured ACTION: <action> and VALUE: <value> (case-insensitive)
    action_match = re.search(r"ACTION:\s*([^\n\r]+)", text, re.IGNORECASE)
    if action_match:
        action = action_match.group(1).strip().upper()
        value = None
        value_match = re.search(r"VALUE:\s*([^\n\r]+)", text, re.IGNORECASE)
        if value_match:
            value = value_match.group(1).strip()
        return action, value

    # Fallback to keyword matching if no structured ACTION is found
    text_lower = text.lower()

    if "volume_up" in text_lower or "increase volume" in text_lower or "louder" in text_lower:
        return "VOLUME_UP", None

    if "volume_down" in text_lower or "decrease volume" in text_lower or "lower" in text_lower:
        return "VOLUME_DOWN", None

    if "mute" in text_lower and "unmute" not in text_lower:
        return "MUTE", None

    if "unmute" in text_lower:
        return "UNMUTE", None

    if "shutdown" in text_lower or "shut down" in text_lower:
        return "SHUTDOWN", None

    if "restart" in text_lower:
        return "RESTART", None

    return None, None


# ---------- VOLUME (CROSS-PLATFORM) ----------
def set_volume(action):
    import subprocess
    try:
        if sys.platform == "win32":
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

        elif sys.platform == "darwin":
            if action == "up":
                subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10)"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                speak("Volume increased")
            elif action == "down":
                subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) - 10)"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                speak("Volume decreased")
            elif action == "mute":
                subprocess.run(["osascript", "-e", "set volume with output muted"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                speak("Muted")
            elif action == "unmute":
                subprocess.run(["osascript", "-e", "set volume without output muted"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                speak("Unmuted")

        elif sys.platform.startswith("linux"):
            # Try pactl first, then fallback to amixer
            try:
                if action == "up":
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif action == "down":
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif action == "mute":
                    subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif action == "unmute":
                    subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                speak(f"Volume {action if action in ['mute', 'unmute'] else action + 'ed'}")
            except Exception:
                try:
                    if action == "up":
                        subprocess.run(["amixer", "set", "Master", "10%+"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    elif action == "down":
                        subprocess.run(["amixer", "set", "Master", "10%-"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    elif action == "mute":
                        subprocess.run(["amixer", "set", "Master", "mute"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    elif action == "unmute":
                        subprocess.run(["amixer", "set", "Master", "unmute"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    speak(f"Volume {action if action in ['mute', 'unmute'] else action + 'ed'}")
                except Exception:
                    speak(f"Volume control not available on Linux without amixer/pactl")

        else:
            speak(f"Volume control not supported on platform {sys.platform}")

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
