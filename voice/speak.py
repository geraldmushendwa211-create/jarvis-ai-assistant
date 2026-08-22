import edge_tts
import asyncio
import threading
import queue
import os
import time
import re
from playsound import playsound

VOICE = "en-GB-RyanNeural"  # British male voice, JARVIS-style
TEMP_DIR = "voice"


def split_into_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s]


async def _generate_speech_file(text, filepath):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(filepath)


def speak(text):
    sentences = split_into_sentences(text)
    if not sentences:
        return
    _run_playback(iter(sentences))


def speak_streaming(sentence_generator):
    """Same as speak(), but takes sentences one at a time as they arrive
    (e.g. from a streaming AI response) instead of a full block of text."""
    _run_playback(sentence_generator)


def _run_playback(sentence_iterable):
    entry_time = time.time()
    file_queue = queue.Queue()

    def worker():
        i = 0
        for sentence in sentence_iterable:
            if not sentence or not sentence.strip():
                continue
            filepath = os.path.join(TEMP_DIR, f"reply_{i}.mp3")
            try:
                asyncio.run(_generate_speech_file(sentence, filepath))
                file_queue.put(filepath)
            except Exception as e:
                print(f"[Speech Generation Error]: {e}")
            i += 1
        file_queue.put(None)

    gen_thread = threading.Thread(target=worker)
    gen_thread.start()

    first_play = True
    while True:
        filepath = file_queue.get()
        if filepath is None:
            break
        try:
            if first_play:
                print(f">>> Time until first speech: {time.time() - entry_time:.2f}s")
                first_play = False
            t0 = time.time()
            playsound(filepath)
            print(f"Played {filepath} in {time.time() - t0:.2f}s")
            os.remove(filepath)
        except Exception as e:
            print(f"[Playback Error]: {e}")

    gen_thread.join()


if __name__ == "__main__":
    speak("Hello Sir Gerald, this is my new natural voice.")