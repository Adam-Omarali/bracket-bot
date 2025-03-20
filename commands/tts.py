from dotenv import load_dotenv
import os
import sys
from elevenlabs.client import ElevenLabs
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from commands.play_audio_buffer import play_audio_elevenlabs

load_dotenv()
api_key = os.getenv("ELEVENLABS_API_KEY")
client = ElevenLabs(
    api_key=api_key,
)

def tts(text: str, voice: str="JBFqnCBsd6RMkjVDRZzb", model: str="eleven_multilingual_v2"):
    audio = client.generate(
        text=text,
        voice=voice,
        model=model
    )
    play_audio_elevenlabs(audio)