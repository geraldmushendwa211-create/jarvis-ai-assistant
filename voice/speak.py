import edge_tts
import asyncio
import threading
import queue
import os
import time
import re
import threading
from dotenv import load_dotenv
from playsound3 import playsound

load_dotenv()

VOICE_OPTIONS = (
    "en-GB-RyanNeural",     # British male
    "en-GB-SoniaNeural",    # British female
    "en-US-GuyNeural",      # American male
    "en-US-AriaNeural",     # American female
    "en-AU-WilliamNeural",  # Australian male
)
VOICE = os.getenv("JARVIS_TTS_VOICE", VOICE_OPTIONS[0])
TEMP_DIR = "voice"
TTS_ENGINE = os.getenv("JARVIS_TTS_ENGINE", "edge").lower()
try:
    TTS_SPEED = min(1.5, max(0.6, float(os.getenv("JARVIS_TTS_SPEED", "0.98"))))
except ValueError:
    TTS_SPEED = 0.98
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "bm_george")
_kokoro_pipeline = None
_kokoro_lock = threading.Lock()


class SentenceSourceError(Exception):
    """The sentence generator itself failed (e.g. the Gemini stream dropped
    mid-reply). Distinct from per-sentence TTS errors, which are logged and
    skipped so playback of the remaining sentences can continue."""


def split_into_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s]


async def _generate_speech_file(text, filepath):
    communicate = edge_tts.Communicate(text, VOICE, rate=_edge_rate())
    await communicate.save(filepath)


def _edge_rate():
    """Convert the shared speed multiplier to Edge TTS's percentage format."""
    return f"{round((TTS_SPEED - 1) * 100):+d}%"


def _get_kokoro_pipeline():
    global _kokoro_pipeline
    if _kokoro_pipeline is None:
        with _kokoro_lock:
            if _kokoro_pipeline is None:
                from kokoro import KPipeline
                _kokoro_pipeline = KPipeline(lang_code="b")
    return _kokoro_pipeline


def _generate_kokoro_speech_file(text, filepath):
    import numpy as np
    import soundfile as sf

    chunks = []
    pipeline = _get_kokoro_pipeline()
    for _graphemes, _phonemes, audio in pipeline(
        text, voice=KOKORO_VOICE, speed=TTS_SPEED, split_pattern=r"\n+"
    ):
        chunks.append(np.asarray(audio))
    if not chunks:
        raise RuntimeError("Kokoro returned no audio")
    sf.write(filepath, np.concatenate(chunks), 24000)


def _generate_audio_file(text, filepath):
    if TTS_ENGINE == "kokoro":
        try:
            _generate_kokoro_speech_file(text, filepath)
            return filepath
        except Exception as error:
            print(f"[Kokoro unavailable, using Edge TTS]: {error}")
            edge_filepath = os.path.splitext(filepath)[0] + ".mp3"
            asyncio.run(_generate_speech_file(text, edge_filepath))
            return edge_filepath
    asyncio.run(_generate_speech_file(text, filepath))
    return filepath


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
                extension = ".wav" if TTS_ENGINE == "kokoro" else ".mp3"
                filepath = os.path.join(TEMP_DIR, f"reply_{i}{extension}")
                try:
                    filepath = _generate_audio_file(sentence, filepath)
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
        except Exception as e:
            print(f"[Playback Error]: {e}")

    gen_thread.join()

    if source_error is not None:
        raise SentenceSourceError(f"sentence source failed: {source_error}") from source_error


if __name__ == "__main__":
    speak("Hello Sir Gerald, this is my new natural voice.")
