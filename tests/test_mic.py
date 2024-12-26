import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import commands.record_audio as mic

if __name__ == "__main__":
    mic.record_audio()  # Record audio from the microphone