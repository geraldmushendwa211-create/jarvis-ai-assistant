import os
from google import genai
from dotenv import load_dotenv

# Load the API key from the .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Create the client using your key
client = genai.Client(api_key=api_key)

# Send a simple test message
response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents="Hello JARVIS, are you working?"
)

# Print the AI's reply
print(response.text)