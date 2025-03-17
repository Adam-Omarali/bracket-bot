#!/usr/bin/env python3

# Adds the lib directory to the Python path
import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import paho.mqtt.client as mqtt
from sshkeyboard import listen_keyboard, stop_listening

# ------------------------------------------------------------------------------------
# Constants & Setup
# ------------------------------------------------------------------------------------
MQTT_BROKER_ADDRESS = "localhost"
# MQTT_TOPIC = "robot/drive"
MQTT_TOPIC = "robot/local_path"
# Create MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Subscribe to the MQTT topic
client.subscribe(MQTT_TOPIC)

client.connect(MQTT_BROKER_ADDRESS)
# client.connect(MQTT_TOPIC)
client.loop_start()


try:
   client.publish(MQTT_TOPIC, json.dumps({"path_xy": [(0, 0), (0, 1), (0, 2)]}))

except Exception as e:
    print(f"Error: {e}")
finally:
    # Clean up
    client.publish(MQTT_TOPIC, "stop")
    client.loop_stop()
    client.disconnect()
    print("Shutdown complete.")
