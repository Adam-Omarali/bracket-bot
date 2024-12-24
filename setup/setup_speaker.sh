#!/bin/bash

# Exit on error
set -e

echo "Installing speaker dependencies..."

# Step 1: Install system dependencies for audio
sudo apt-get update
sudo apt-get install -y python3-pyaudio libportaudio2 libportaudiocpp0 portaudio19-dev libsndfile1

# Step 2: Update pip
pip3 install --upgrade pip

# Step 3: Install Python audio and sound packages
pip3 install pyaudio pyalsaaudio elevenlabs sounddevice soundfile python-dotenv

# Step 4: Run ALSA volume setup script
ALSAVOL_SCRIPT="$(dirname "$0")/set_alsa_volume.py"
[ -f "$ALSAVOL_SCRIPT" ] || { echo "Error: '$ALSAVOL_SCRIPT' not found. Exiting."; exit 1; }

echo "Running ALSA volume setup script..."
python3 "$ALSAVOL_SCRIPT"

echo "Speaker setup complete!"

# Step 5: Test imports
python3 -c "import sounddevice; import soundfile; import elevenlabs; print('Speaker packages installation successful!')"
