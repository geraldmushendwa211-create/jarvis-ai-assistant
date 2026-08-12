import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

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
        "system_instruction": "You are JARVIS, a helpful AI assistant. Always address the user as 'Sir Gerald'. Keep a polite, slightly formal and witty tone, similar to a butler."
    },
    history=history
)

print("JARVIS is online. Type 'quit' to exit.\n")

while True:
    user_input = input("You: ")

    if user_input.lower() == "quit":
        print("JARVIS: Goodbye, Sir Gerald.")
        break

    response = chat.send_message(user_input)
    print("JARVIS:", response.text)

    # Save the updated conversation history to file
    updated_history = [
        {"role": msg.role, "parts": [{"text": part.text} for part in msg.parts]}
        for msg in chat.get_history()
    ]
    with open(MEMORY_FILE, "w") as f:
        json.dump(updated_history, f, indent=2)