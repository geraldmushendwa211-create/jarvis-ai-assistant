import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import speech_recognition as sr

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 90   # tuned based on mic calibration
SILENCE_DURATION = 1.2    # seconds of quiet before it decides you're done
CHUNK_DURATION = 0.1
MAX_WAIT = 8               # give up if you never start speaking

def record_audio(filename="voice/temp.wav"):
    print("Listening... speak now.")
    recording = []
    silence_chunks = 0
    silence_limit = int(SILENCE_DURATION / CHUNK_DURATION)
    speaking_started = False
    elapsed = 0

    def callback(indata, frames, time, status):
        nonlocal silence_chunks, speaking_started
        volume = np.abs(indata).mean()
        recording.append(indata.copy())
        if volume > SILENCE_THRESHOLD:
            speaking_started = True
            silence_chunks = 0
        elif speaking_started:
            silence_chunks += 1

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16',
                         blocksize=int(SAMPLE_RATE * CHUNK_DURATION),
                         callback=callback):
        while True:
            sd.sleep(int(CHUNK_DURATION * 1000))
            elapsed += CHUNK_DURATION
            if speaking_started and silence_chunks >= silence_limit:
                break
            if not speaking_started and elapsed >= MAX_WAIT:
                break

    print("Done recording.")
    if not recording:
        write(filename, SAMPLE_RATE, np.zeros((1, 1), dtype='int16'))
        return filename
    audio_data = np.concatenate(recording, axis=0)
    write(filename, SAMPLE_RATE, audio_data)
    return filename

def transcribe_audio(filename="voice/temp.wav"):
    recognizer = sr.Recognizer()
    with sr.AudioFile(filename) as source:
        audio_data = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio_data)
        return text
    except sr.UnknownValueError:
        return "Sorry, I couldn't understand that."
    except sr.RequestError:
        return "Speech recognition service is unavailable."

if __name__ == "__main__":
    file = record_audio()
    result = transcribe_audio(file)
    print("You said:", result)