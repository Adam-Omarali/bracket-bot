import time  # Import time for adding delays
from elevenlabs.client import ElevenLabs
import os
from io import BytesIO
import sounddevice as sd
import soundfile as sf
import numpy as np
from scipy import signal

def play_audio_elevenlabs(audio, volume_increase=3.0):
    # Set the desired audio device
    device_name = "UACDemoV1.0"  # Name of the USB audio device
    device_info = sd.query_devices(device_name, 'output')
    device_id = device_info['index']
    device_sample_rate = device_info['default_samplerate']

    audio_data = b''.join(audio)
    data, sample_rate = sf.read(BytesIO(audio_data), dtype='float32')

    # Resample if necessary
    if sample_rate != device_sample_rate:
        print(f"Resampling from {sample_rate} to {device_sample_rate}")
        number_of_samples = int(round(len(data) * float(device_sample_rate) / sample_rate))
        data = signal.resample(data, number_of_samples)
        sample_rate = device_sample_rate

    data = data * volume_increase

    try:
        # Play the audio using the specified device
        sd.play(data, samplerate=sample_rate, device=device_id)
        sd.wait()
        print("Audio played successfully")
    except sd.PortAudioError as e:
        print(f"Error playing audio: {e}")
        print(f"Supported sample rates for this device: {device_sample_rate}")

# Function to play audio
def play_audio_gpt(audio, volume_increase=3.0):
    # Set the desired audio device
    device_name = "UACDemoV1.0"  # Name of the USB audio device
    device_info = sd.query_devices(device_name, 'output')
    device_id = device_info['index']
    device_sample_rate = device_info['default_samplerate']

    data, sample_rate = sf.read(BytesIO(audio), dtype='float32')

    # Resample if necessary
    if sample_rate != device_sample_rate:
        print(f"Resampling from {sample_rate} to {device_sample_rate}")
        number_of_samples = int(round(len(data) * float(device_sample_rate) / sample_rate))
        data = signal.resample(data, number_of_samples)
        sample_rate = device_sample_rate

    data = data * volume_increase

    try:
        # Play the audio using the specified device
        sd.play(data, samplerate=sample_rate, device=device_id)
        sd.wait()
        print("Audio played successfully")
    except sd.PortAudioError as e:
        print(f"Error playing audio: {e}")
        print(f"Supported sample rates for this device: {device_sample_rate}")