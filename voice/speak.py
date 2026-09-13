import edge_tts
import asyncio
import threading
import queue
import os
import time
import re
from playsound3 import playsound

VOICE = "en-GB-RyanNeural"  # British male voice, JARVIS-style
TEMP_DIR = "voice"


class SentenceSourceError(Exception):
    """The sentence generator itself failed (e.g. the Gemini stream dropped
    mid-reply). Distinct from per-sentence TTS errors, which are logged and
    skipped so playback of the remaining sentences can continue."""


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
    (e.g. from a streaming AI response) instead of a full block of text.

    Raises SentenceSourceError if the generator fails partway — after playing
    whatever sentences already arrived.
    """
    _run_playback(sentence_generator)


def _run_playback(sentence_iterable):
    entry_time = time.time()
    file_queue = queue.Queue()

    def worker():
        i = 0
        try:
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
        except Exception as e:
            # The sentence source blew up (e.g. Gemini stream dropped).
            # Forward the failure so the caller can report it...
            file_queue.put(e)
        finally:
            # ...but ALWAYS release the consumer, or it waits forever.
            file_queue.put(None)

    gen_thread = threading.Thread(target=worker)
    gen_thread.start()

    source_error = None
    first_play = True
    while True:
        item = file_queue.get()
        if item is None:
            break
        if isinstance(item, Exception):
            source_error = item
            continue  # keep draining until the sentinel arrives
        filepath = item
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

    if source_error is not None:
        raise SentenceSourceError(f"sentence source failed: {source_error}") from source_error


if __name__ == "__main__":
    speak("Hello Sir Gerald, this is my new natural voice.")
