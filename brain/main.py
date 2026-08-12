import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from voice.listen import record_audio, transcribe_audio
from voice.speak import speak
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

print("JARVIS is online. Type 'quit' to exit.\n")

while True:
    file = record_audio()
    user_input = transcribe_audio(file)
    print("You:", user_input)

    if user_input.lower() == "quit":
        print("JARVIS: Goodbye, Sir Gerald.")
        break

    response = chat.send_message(user_input)
    print("JARVIS:", response.text)
    speak(response.text)

    # Save the updated conversation history to file
    updated_history = [
        {"role": msg.role, "parts": [{"text": part.text} for part in msg.parts]}
        for msg in chat.get_history()
    ]
    with open(MEMORY_FILE, "w") as f:
        json.dump(updated_history, f, indent=2)