import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import commands.play_audio_file as play

if __name__ == "__main__":
    play.play_audio_file(path="examples/game_sounds/amongus.wav")