import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import commands.text_to_speech as tts

if __name__ == "__main__":
    tts.tts("Hello, world!")  # Speak "Hello, world!" to the user