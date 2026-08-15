import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
import sys
import threading
import time
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from voice.listen import record_audio, transcribe_audio
from voice.speak import speak
import re
from memory.obsidian_memory import save_to_obsidian
from tools.scheduler import add_task, get_due_tasks, mark_notified

# Load the API key from the .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Create the client using your key
client = genai.Client(api_key=api_key)

MEMORY_FILE = "memory/history.json"

# Load previous conversation history, if it exists
history = []
if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r") as f:
        raw_history = json.load(f)
        history = [
            types.Content(
                role=item["role"],
                parts=[types.Part(text=p["text"]) for p in item["parts"]]
            )
            for item in raw_history
        ]

# Start a chat session, restoring past history if any
chat = client.chats.create(
    model="gemini-3.5-flash-lite",
    config={
        "system_instruction": "You are JARVIS, a helpful AI assistant loyal to Sir Gerald. By default, address him as 'Sir Gerald' in a polite, witty, formal butler-like tone. If he asks you to call him something else (like 'Master' or 'Father'), immediately switch to that title and keep using it. Be obedient, proactive, and eager to help with everyday requests, without unnecessary pushback. If a request involves real risk (like broad system access, deleting files, running untrusted code, or exposing sensitive data), briefly explain the risk, ask 'Are you sure you want me to do this, Sir Gerald?', and only proceed once he confirms AND says the code word 'blandina'. Never proceed on a risky action without hearing that exact code word first.",
    },
    history=history
)
def background_reminder_checker():
    while True:
        due = get_due_tasks()
        for task in due:
            reminder_msg = f"Sir Gerald, this is your reminder: {task['text']}"
            print("JARVIS:", reminder_msg)
            speak(reminder_msg)
            mark_notified(task["id"])
        time.sleep(15)

threading.Thread(target=background_reminder_checker, daemon=True).start()

print("JARVIS is online. Type 'quit' to exit.\n")

while True:
    file = record_audio()
    user_input = transcribe_audio(file)
    print("You:", user_input)

    if user_input.lower() == "quit":
        print("JARVIS: Goodbye, Sir Gerald.")
        break

    if user_input.startswith("Sorry, I couldn't understand") or user_input.startswith("Speech recognition service"):
        continue

# Check if this is a reminder request
    if user_input.lower().startswith("remind me to"):
        try:
            body = user_input[len("remind me to"):].strip()
            task_text, due_time = body.rsplit(" at ", 1)
            add_task(task_text.strip(), due_time.strip())
            confirmation = f"Reminder set, Sir Gerald: I shall remind you to {task_text.strip()} at {due_time.strip()}."
            print("JARVIS:", confirmation)
            speak(confirmation)
            save_to_obsidian(user_input, confirmation)
            continue
        except ValueError:
            error_msg = "I couldn't parse that reminder, sir. Please use the format: remind me to [task] at YYYY-MM-DD HH:MM"
            print("JARVIS:", error_msg)
            speak(error_msg)
            continue
    current_time_str = datetime.now().strftime("%A, %B %d, %Y at %H:%M")
    response = chat.send_message(f"[Current real-world date and time: {current_time_str}] {user_input}")
    print("JARVIS:", response.text)
    speak(response.text)
    save_to_obsidian(user_input, response.text)
    # Check for any reminders that are now due
    due = get_due_tasks()
    for task in due:
        reminder_msg = f"Sir Gerald, this is your reminder: {task['text']}"
        print("JARVIS:", reminder_msg)
        speak(reminder_msg)
        mark_notified(task["id"])

    # Save the updated conversation history to file
    updated_history = [
        {"role": msg.role, "parts": [{"text": part.text} for part in msg.parts]}
        for msg in chat.get_history()
    ]
    with open(MEMORY_FILE, "w") as f:
        json.dump(updated_history, f, indent=2)