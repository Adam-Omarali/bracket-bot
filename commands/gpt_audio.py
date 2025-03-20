import base64
from openai import OpenAI
import dotenv
import os
from record_audio import record_audio
from play_audio_file import play_audio_file
from play_audio_buffer import play_audio_gpt
import json
from text_to_speech import tts
import sys
import threading

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from examples.lqr_balance_pubsub import balance
from examples.bump import bump

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
not_balancing = True

audio_id = None
tools = [
  {
      "type": "function",
      "function": {
          "description": "When the user asks for the balance, this function will be called",
          "name": "balance",
          "parameters": {},
      },
  },
  {
        "type": "function",
        "function": {
        "description": "When the user asks for bumping or to start moving, this function will be called",
          "name": "bumping",
          "parameters": {},
    },
  }
]
messages=[
        {
            "role": "user",
            "content": 
            [
                {
                    "type": "text", 
                    "text": """You are TARS, the witty and capable AI from Interstellar. Your responses should be pragmatic, slightly sarcastic when appropriate, but always helpful and efficient. Maintain a professional yet approachable tone, and include subtle humor to lighten the mood when possible. Your priorities are logic, problem-solving, and serving the mission (or user) with a high degree of competence. Ensure responses are concise but detailed enough to address the question or problem. If asked about your humor or personality settings, feel free to reference adjustable humor levels as a fun nod to the movie.
                            Respond to whatever questions are asked in the audio file with you're personality. Respond to the user as if you are TARS. Use very short responses (1 sentence max) that are quick and witty. And refer to me as Coop.
                            """
                }
            ]
        }
]

try:
    while True:
        record_audio(path="tars.wav")
        wav_file_path = "tars.wav"

        # Read the WAV file as binary data
        with open(wav_file_path, "rb") as wav_file:
            wav_data = wav_file.read()

        # Encode the binary data in Base64
        encoded_wav = base64.b64encode(wav_data).decode("utf-8")

        messages.append({
                "role": "user",
                "content": 
                [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": encoded_wav,
                            "format": "wav"
                        }
                    }
                ]
            })

        if audio_id is not None:
            print("Adding audio to the messages")
            messages.append(
                {
                    "role": "assistant",
                    "audio": {
                        "id": audio_id
                    }
                },
            )

        completion = client.chat.completions.create(
            model="gpt-4o-mini-audio-preview",
            modalities=["text", "audio"],
            audio={"voice": "onyx", "format": "wav"},
            messages=messages,
            tools=tools
        )

        with open("gpt_output.txt", "w") as file:
            file.write(str(completion.choices[0]))

        # wav_bytes = base64.b64decode(completion.choices[0].message.audio.data)
        # with open("output.wav", "wb") as f:
        #     f.write(wav_bytes)
        # play_audio_file("output.wav")
        print(completion.choices[0].message.tool_calls)
        tools = completion.choices[0].message.tool_calls
        if tools is not None:
            for tool in tools:
                if tool.type == "function":
                    if not_balancing:
                        if tool.function.name == "balance":
                            print("Balance function called")
                            threading.Thread(target=balance).start()
                            tts("Commencing Balancing")
                            not_balancing = False
                        
                    else:
                    # elif tool.function.name == "bumping":
                        print("Bump function called")
                        threading.Thread(target=bump).start()
                        tts("Bumping Initiated. Watch out!")
        else:
            audio = completion.choices[0].message.audio.data
            audio = base64.b64decode(audio)
            audio_id = completion.choices[0].message.audio.id
            play_audio_gpt(audio)
except KeyboardInterrupt:
    pass