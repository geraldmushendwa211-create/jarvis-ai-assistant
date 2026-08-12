import pyttsx3

def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 175)  # speaking speed
    engine.say(text)
    engine.runAndWait()

if __name__ == "__main__":
    speak("Hello Sir Gerald, I am now able to speak.")