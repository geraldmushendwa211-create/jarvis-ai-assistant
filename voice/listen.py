import sounddevice as sd
from scipy.io.wavfile import write
import speech_recognition as sr

SAMPLE_RATE = 16000  # standard rate for speech recognition
DURATION = 5         # seconds to record

def record_audio(filename="voice/temp.wav"):
    print("Listening... speak now.")
    audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
    sd.wait()  # wait until recording is finished
    write(filename, SAMPLE_RATE, audio)
    print("Done recording.")
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