import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
import sys
import threading
import time
from datetime import datetime, timedelta
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from voice.listen import record_audio, transcribe_audio
from voice.speak import speak, speak_streaming
import re
from memory.obsidian_memory import save_to_obsidian
from tools.scheduler import add_task, get_due_tasks, mark_notified
from core.permissions import request_permission, APPROVAL_REQUIRED, SAFE
from core.skill_manager import find_matching_skill
import skills.test_skill  # importing a skill file registers it automatically
import skills.roblox_creator
from interface.status_window import start as start_status_window, set_state

start_status_window()
set_state("IDLE")

# Load the API key from the .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Create the client using your key
client = genai.Client(api_key=api_key)

MEMORY_FILE = "memory/history.json"
MAX_HISTORY_ENTRIES = 20  # roughly the last 10 back-and-forth exchanges — keeps latency from growing every turn

JARVIS_CONFIG = types.GenerateContentConfig(
    system_instruction="You are JARVIS, a helpful AI assistant loyal to Sir Gerald. By default, address him as 'Sir Gerald' in a polite, witty, formal butler-like tone. If he asks you to call him something else (like 'Master' or 'Father'), immediately switch to that title and keep using it. Be obedient, proactive, and eager to help with everyday requests, without unnecessary pushback. If a request involves real risk (like broad system access, deleting files, running untrusted code, or exposing sensitive data), briefly explain the risk, ask 'Are you sure you want me to do this, Sir Gerald?', and only proceed once he confirms AND says the code word 'blandina'. Never proceed on a risky action without hearing that exact code word first.",
    thinking_config=types.ThinkingConfig(thinking_level="low"),
)

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

history = history[-MAX_HISTORY_ENTRIES:]

# Start a chat session, restoring past history if any
chat = client.chats.create(
    model="gemini-3.5-flash",
    config=JARVIS_CONFIG,
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
    set_state("LISTENING")
    file = record_audio()
    t0 = time.time()
    user_input = transcribe_audio(file)
    print("Transcribe:", time.time() - t0)
    print("You:", user_input)

    if user_input.lower() == "quit":
        print("JARVIS: Goodbye, Sir Gerald.")
        set_state("IDLE", "Shutting down.")
        break

    if user_input.startswith("Sorry, I couldn't understand") or user_input.startswith("Speech recognition service"):
        set_state("IDLE")
        continue

    set_state("THINKING", user_input)

    # Check if any registered skill matches this input
    matched_skill = find_matching_skill(user_input)
    if matched_skill:
        set_state("EXECUTING", f"Running skill: {matched_skill['name']}")
        allowed = request_permission(
            action=f"Run skill: {matched_skill['name']}",
            reason=f"You said something matching this skill's trigger phrase.",
            level=matched_skill["permission_level"],
        )
        if allowed:
            skill_response = matched_skill["handler"](user_input, gemini_client=client)
            set_state("SUCCESS", f"{matched_skill['name']} completed.")
        else:
            skill_response = f"Permission denied, Sir Gerald. I will not run the {matched_skill['name']} skill."
            set_state("ERROR", "Permission denied.")
        print("JARVIS:", skill_response)
        speak(skill_response)
        save_to_obsidian(user_input, skill_response)
        set_state("IDLE")
        continue

    # Check if this is a reminder request
    if "remind me to" in user_input.lower():
        trigger_idx = user_input.lower().index("remind me to")
        body_full = user_input[trigger_idx + len("remind me to"):].strip()
        relative_match = re.search(r"(.+?)\s+in\s+(\d+)\s*(minute|minutes|min|hour|hours|hr|hrs)$", body_full, re.IGNORECASE)
        if relative_match:
            task_text = relative_match.group(1).strip()
            amount = int(relative_match.group(2))
            unit = relative_match.group(3).lower()
            if "hour" in unit or "hr" in unit:
                due_dt = datetime.now() + timedelta(hours=amount)
            else:
                due_dt = datetime.now() + timedelta(minutes=amount)
            due_time = due_dt.strftime("%Y-%m-%d %H:%M")
            add_task(task_text, due_time)
            confirmation = f"Reminder set, Sir Gerald: I shall remind you to {task_text} at {due_time}."
            print("JARVIS:", confirmation)
            speak(confirmation)
            save_to_obsidian(user_input, confirmation)
            set_state("IDLE")
            continue
        else:
            try:
                task_text, due_time = body_full.rsplit(" at ", 1)
                task_text = task_text.strip()
                due_time = due_time.strip()
                add_task(task_text, due_time)
                confirmation = f"Reminder set, Sir Gerald: I shall remind you to {task_text} at {due_time}."
                print("JARVIS:", confirmation)
                speak(confirmation)
                save_to_obsidian(user_input, confirmation)
                set_state("IDLE")
                continue
            except ValueError:
                error_msg = "I couldn't parse that reminder, sir. Try: remind me to [task] in [number] minutes, or remind me to [task] at YYYY-MM-DD HH:MM"
                print("JARVIS:", error_msg)
                speak(error_msg)
                set_state("IDLE")
                continue

    # Check if this is a delete request (SENSITIVE — goes through permission system)
    if user_input.lower().startswith("delete "):
        target_file = user_input[len("delete "):].strip()
        allowed = request_permission(
            action=f"Delete the file '{target_file}'",
            reason="You asked me to delete this file.",
            level=APPROVAL_REQUIRED,
        )
        if allowed:
            confirmation = f"Understood, Sir Gerald. I have deleted '{target_file}'. (This is a test — no file was actually touched yet.)"
        else:
            confirmation = f"Permission denied, Sir Gerald. I will not delete '{target_file}'."
        print("JARVIS:", confirmation)
        speak(confirmation)
        save_to_obsidian(user_input, confirmation)
        set_state("IDLE")
        continue

    current_time_str = datetime.now().strftime("%A, %B %d, %Y at %H:%M")
    t1 = time.time()

    try:
        full_response_parts = []
        timing = {"first_chunk": None}

        def sentence_stream():
            buffer = ""
            for chunk in chat.send_message_stream(f"[Current real-world date and time: {current_time_str}] {user_input}"):
                if timing["first_chunk"] is None:
                    timing["first_chunk"] = time.time()
                    print(f">>> Time to FIRST Gemini chunk: {timing['first_chunk'] - t1:.2f}s")
                if not chunk.text:
                    continue
                full_response_parts.append(chunk.text)
                buffer += chunk.text
                while True:
                    match = re.search(r"[.!?](\s|$)", buffer)
                    if not match:
                        break
                    idx = match.end()
                    sentence = buffer[:idx].strip()
                    buffer = buffer[idx:]
                    if sentence:
                        yield sentence
            if buffer.strip():
                yield buffer.strip()
            print(f">>> Time for FULL Gemini stream to finish: {time.time() - t1:.2f}s")

        speak_streaming(sentence_stream())
        print("Gemini+Speak total:", time.time() - t1)

        response_text = "".join(full_response_parts)
        print("JARVIS:", response_text)
        save_to_obsidian(user_input, response_text)
        set_state("IDLE")

        # Check for any reminders that are now due
        due = get_due_tasks()
        for task in due:
            reminder_msg = f"Sir Gerald, this is your reminder: {task['text']}"
            print("JARVIS:", reminder_msg)
            speak(reminder_msg)
            mark_notified(task["id"])

        # Save the updated conversation history to file, trimmed to the last
        # MAX_HISTORY_ENTRIES so context (and latency) doesn't keep growing
        updated_history = [
            {"role": msg.role, "parts": [{"text": part.text} for part in msg.parts]}
            for msg in chat.get_history()
        ]
        updated_history = updated_history[-MAX_HISTORY_ENTRIES:]
        with open(MEMORY_FILE, "w") as f:
            json.dump(updated_history, f, indent=2)

        # Rebuild the chat session from the trimmed history, so the next turn
        # starts lean instead of carrying the full growing conversation forward
        trimmed_content_history = [
            types.Content(
                role=item["role"],
                parts=[types.Part(text=p["text"]) for p in item["parts"]]
            )
            for item in updated_history
        ]
        chat = client.chats.create(
            model="gemini-3.5-flash",
            config=JARVIS_CONFIG,
            history=trimmed_content_history
        )

    except Exception as e:
        # Google's servers can be temporarily overloaded (503s like we just
        # hit), or the network can drop mid-response. Fail safely instead of
        # crashing the whole assistant.
        print("Gemini call failed:", e)
        set_state("ERROR", "AI service temporarily unavailable.")
        speak("I'm having trouble reaching my AI service right now, Sir Gerald. Please try again in a moment.")
        set_state("IDLE")