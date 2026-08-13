import sounddevice as sd
import numpy as np

SAMPLE_RATE = 16000
CHUNK_DURATION = 0.1

def callback(indata, frames, time, status):
    volume = np.abs(indata).mean()
    print(f"Volume: {volume:.1f}")

print("Stay silent for 3 seconds, then talk normally. Press Ctrl+C to stop.")
with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16',
                     blocksize=int(SAMPLE_RATE * CHUNK_DURATION),
                     callback=callback):
    sd.sleep(10000)