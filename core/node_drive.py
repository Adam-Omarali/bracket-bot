#!/usr/bin/env python3

# Adds the lib directory to the Python path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import sys
import os
import json
import time
import paho.mqtt.client as mqtt
from lib.odrive_uart import ODriveUART

# Constants
MQTT_BROKER_ADDRESS = "localhost"
MQTT_TOPIC = "robot/drive"
LINEAR_SPEED = 0.3
ANGULAR_SPEED = 1
WHEEL_BASE = 0.4

# Load motor directions from JSON
def load_motor_dirs():
    try:
        with open(os.path.expanduser('~/quickstart/lib/motor_dir.json'), 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading motor_dir.json: {e}")
        raise

motor_dirs = load_motor_dirs()

# Initialize motor controller
motor_controller = ODriveUART(
    port='/dev/ttyAMA1',
    left_axis=0, right_axis=1,
    dir_left=motor_dirs['left'], dir_right=motor_dirs['right']
)

# Start motors and set mode
motor_controller.start_left()
motor_controller.start_right()
motor_controller.enable_velocity_mode_left()
motor_controller.enable_velocity_mode_right()
motor_controller.disable_watchdog_left()
motor_controller.disable_watchdog_right()

# Clear motor errors
motor_controller.clear_errors_left()
motor_controller.clear_errors_right()

# Set velocities for the motors
def set_velocity(linear, angular):
    left = linear - (WHEEL_BASE / 2) * angular
    right = linear + (WHEEL_BASE / 2) * angular
    motor_controller.set_speed_mps_left(left)
    motor_controller.set_speed_mps_right(right)
    print(f"Set speeds: Left={left} m/s, Right={right} m/s")

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    payload = msg.payload.decode().strip().lower()
    print(f"Received: {payload}")

    try:
        # Handle JSON command
        data = json.loads(payload)
        if 'linear_velocity' in data and 'angular_velocity' in data:
            set_velocity(data['linear_velocity'], data['angular_velocity'])
    except json.JSONDecodeError:
        # Handle simple text commands
        command_map = {
            "forward": (LINEAR_SPEED, 0),
            "back": (-LINEAR_SPEED, 0),
            "left": (0, ANGULAR_SPEED),
            "right": (0, -ANGULAR_SPEED),
            "stop": (0, 0)
        }
        if payload in command_map:
            set_velocity(*command_map[payload])

# Main loop
def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER_ADDRESS)
        client.loop_start()
        print("Listening for commands... Press Ctrl+C to exit.")
        
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("Exiting...")
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Stop motors and clean up
        motor_controller.set_speed_mps_left(0)
        motor_controller.set_speed_mps_right(0)
        client.loop_stop()
        client.disconnect()
        motor_controller.clear_errors_left()
        motor_controller.clear_errors_right()
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
