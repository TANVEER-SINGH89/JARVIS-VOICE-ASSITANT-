Jarvis – AI Voice Assistant (Python)

A production-style AI-powered voice assistant built in Python that demonstrates real-world skills in speech processing, API integration, multithreading, and system-level automation on Windows.

**Why This Project Matters**

This project showcases the ability to:

Build end-to-end applications, not just scripts

Work with real hardware input (microphone, speakers)

Integrate external AI APIs securely

Design modular, maintainable code

Handle concurrency and OS-level controls

**Key Features**

Wake-word based activation (Jarvis)

Real-time speech recognition

Non-blocking text-to-speech using multithreading

AI-driven responses via OpenRouter LLM API

System volume control (up/down/mute/unmute)

Command routing & intent handling

Secure API key handling via environment variables

Clean exit and interruption handling

**Technical Highlights**

Multithreading used to prevent TTS from blocking command execution

Thread-safe audio engine control with locks

Regex-based response sanitization for clean speech output

Low-latency voice interaction loop

Separation of concerns (speech, AI, system control)

**Tech Stack**
Category	Tools
Language	Python 3
Voice Input	SpeechRecognition
Voice Output	pyttsx3
AI / LLM	OpenRouter API (DeepSeek model)
System Control	pycaw (Windows Core Audio)
Networking	requests
Concurrency	threading
**Project Structure**
Jarvis/
├── jarvis.py          # Core application logic
├── requirements.txt  # Dependency list
└── README.md         # Project documentation

**Setup & Installation**
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd Jarvis
pip install -r requirements.txt

Secure API Configuration

API keys are never hard-coded.

Set environment variable:

Windows (PowerShell)

**setx OPENROUTER_API_KEY "your_api_key_here"**


This demonstrates secure credential management, a production best practice.

Running the Application
python jarvis.py



**Platform Compatibility**

✅ Windows (full functionality)

❌ Linux / macOS (volume control limited)

Engineering Skills Demonstrated

API integration

Multithreaded programming

Audio processing

OS-level automation

Secure configuration management

Clean, readable Python code

Debugging real-world runtime issues

Future Improvements

Cross-platform support

Offline AI inference

Application launcher

GUI interface

Plugin-based command system
