import os
from google import genai
from dotenv import load_dotenv

# Load the API key from the .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Create the client using your key
client = genai.Client(api_key=api_key)

# Start a chat session (this remembers the conversation history)
chat = client.chats.create(
    model="gemini-3.5-flash-lite",
    config={
        "system_instruction": "You are JARVIS, a helpful AI assistant. Always address the user as 'Sir Gerald'. Keep a polite, slightly formal and witty tone, similar to a butler."
    }
)
print("JARVIS is online. Type 'quit' to exit.\n")

# Loop forever until the user types "quit"
while True:
    user_input = input("You: ")

    if user_input.lower() == "quit":
        print("JARVIS: Goodbye, Gerald.")
        break

    response = chat.send_message(user_input)
    print("JARVIS:", response.text)