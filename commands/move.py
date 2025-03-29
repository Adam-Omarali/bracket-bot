import sys
import os
import threading
import paho.mqtt.client as mqtt
import numpy as np
import cv2
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from examples.drive_controller import RobotController

# MQTT settings
MQTT_BROKER_ADDRESS = "localhost"
MQTT_TOPIC_DEPTH = "robot/frame/depth"
MQTT_TOPIC_COLOR = "robot/frame/color"

# Global variable to store the latest depth frame
current_depth_frame = None

def setup_mqtt():
    client = mqtt.Client()
    client.connect(MQTT_BROKER_ADDRESS, 1883, 60)
    client.subscribe(MQTT_TOPIC_DEPTH, 0)
    
    def on_message(client, userdata, msg):
        global current_depth_frame
        # Convert received bytes back to image
        nparr = np.frombuffer(msg.payload, np.uint8)
        current_depth_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    client.on_message = on_message
    client.loop_start()
    return client

# Initialize MQTT client
mqtt_client = setup_mqtt()

def move(distance, angle):
    controller = RobotController()
    # controller.drive_distance(distance)
    threading.Thread(target=controller.turn_degrees, args=(angle,)).start()
    controller.stop_motors()

def move_until_close(threshold_distance=0.1, speed=0.5):
    """
    Move forward until an object is detected within threshold_distance (in meters)
    Args:
        threshold_distance: Distance in meters to stop at
        speed: Speed to move at (0.0 to 1.0)
    """
    controller = RobotController()
    controller.start_motors()
    
    try:
        while True:
            if current_depth_frame is None:
                continue
            
            # Calculate the average depth in the center region of the frame
            height, width = current_depth_frame.shape[:2]
            center_region = current_depth_frame[height//3:2*height//3, width//3:2*width//3]
            avg_depth = np.mean(center_region) * 0.001  # Convert mm to meters
            
            print(f"Current depth: {avg_depth:.2f}m")
            
            if avg_depth <= threshold_distance:
                print(f"Object detected at {avg_depth:.2f}m - stopping")
                break
                
            # Move forward
            controller.set_motor_speeds(speed, speed)
            
    finally:
        controller.stop_motors()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

if __name__ == "__main__":
    # Example usage: move until object is 0.5 meters away
    move_until_close(threshold_distance=0.08, speed=0.3)