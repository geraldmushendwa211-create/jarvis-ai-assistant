import edge_tts
import asyncio
from playsound import playsound
import os

VOICE = "en-GB-RyanNeural"  # British male voice, JARVIS-style
TEMP_FILE = "voice/reply.mp3"

async def _generate_speech(text):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(TEMP_FILE)

def speak(text):
    asyncio.run(_generate_speech(text))
    playsound(TEMP_FILE)
    os.remove(TEMP_FILE)

if __name__ == "__main__":
    speak("Hello Sir Gerald, this is my new natural voice.")