import cv2
from ultralytics import YOLO
import json
import time


# Adds the lib directory to the Python path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import paho.mqtt.client as mqtt
from subsystem.Vision import Vision

# ------------------------------------------------------------------------------------
# Constants & Setup
# ------------------------------------------------------------------------------------
MQTT_BROKER_ADDRESS = "localhost"
MQTT_TOPIC = "robot/drive"
MQTT_TOPIC_BOTTLE = "robot/bottle_position"
MQTT_PROCESSED_FRAME = "robot/processed_frame"

# Create MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_BROKER_ADDRESS)
client.loop_start()


# Add to globals at the top
current_path = None
following_path = False
    

def home_towards_bottle(bottle_coords):
    """
    Publishes direct drive commands to move towards the bottle coordinates
    """
    if not bottle_coords:
        # No bottle detected, stop moving
        cmd = {'linear_velocity': 0.0, 'angular_velocity': 0.0}
        client.publish(MQTT_TOPIC, json.dumps(cmd))
        return

    # Extract bottle center position
    x1, y1, x2, y2 = bottle_coords
    bottle_center_x = (x1 + x2) // 2
    frame_width = 640  # Assuming standard camera width

    # Calculate normalized position (-1 to 1)
    normalized_x = (bottle_center_x / frame_width * 2) - 1

    # Set movement speeds
    linear_speed = 0.35  # Forward speed
    angular_speed = 0.7  # Turning speed
    
    # Determine movement based on bottle position
    if abs(normalized_x) < 0.2:  # Bottle is roughly centered
        cmd = {'linear_velocity': linear_speed, 'angular_velocity': 0.0}
    elif normalized_x < 0:  # Bottle is to the left
        cmd = {'linear_velocity': linear_speed * 0.5, 'angular_velocity': angular_speed}
    else:  # Bottle is to the right
        cmd = {'linear_velocity': linear_speed * 0.5, 'angular_velocity': -angular_speed}

    # Publish drive command
    client.publish(MQTT_TOPIC, json.dumps(cmd))


def get_bounding_boxes(frame, model):

    # Run YOLO inference
    results = model(frame)
    
    objects = [0, 0, 0]
    bottle_coords = None

    # Draw bounding boxes on the frame
    for i in range(len(results)):
        if (i > 3):
            break
        result = results[i]
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])  # Bounding box coordinates
            conf = box.conf[0]  # Confidence score
            cls = int(box.cls[0])  # Class index
            
            objects[i] = {"coords": [x1, y1, x2, y2], "conf": conf, "class": model.names[cls]}
            print(f"object{i}: confidence:", conf, "class:", model.names[cls])
            
            # Store coordinates if object is a bottle
            if model.names[cls].lower() == "bottle" and conf > 0.6:  # Added confidence threshold
                bottle_coords = [x1, y1, x2, y2]
                print(f"[yolo_custom.py] Bottle detected with confidence: {conf:.2f}")
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{model.names[cls]} {conf:.2f}", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # client.publish(MQTT_PROCESSED_FRAME, frame)
        cv2.imwrite('img.jpg', frame)
    # Get movement direction based on bottle position
    # move_towards_bottle(frame_width, bottle_coords)
    return bottle_coords



model = YOLO("best_bottle.pt", task="detect")  # Replace with your trained model path


# vision = Vision()
cap = cv2.VideoCapture(0)
while True:
    
    # ret,frame = vision.get_frame()
    ret,frame = cap.read()
    if not ret:
        client.disconnect()
        break
    bottle_coords = get_bounding_boxes(frame, model)
    home_towards_bottle(bottle_coords)
