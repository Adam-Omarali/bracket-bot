import cv2
from ultralytics import YOLO
import json
import time


# Adds the lib directory to the Python path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import paho.mqtt.client as mqtt
from sshkeyboard import listen_keyboard, stop_listening
from subsystem.Vision import Vision

# ------------------------------------------------------------------------------------
# Constants & Setup
# ------------------------------------------------------------------------------------
MQTT_BROKER_ADDRESS = "localhost"
MQTT_TOPIC = "robot/drive"
MQTT_TOPIC_BOTTLE = "robot/bottle_position"
MQTT_TOPIC_PATH_PLAN = "robot/local_path"
MQTT_TOPIC_PATH_COMPLETED = "robot/path_completed"

# Create MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_BROKER_ADDRESS)
client.loop_start()

# def press(key):
#     if key.lower() == 'w':  # Forward
#         client.publish(MQTT_TOPIC, "forward")
#     elif key.lower() == 's':  # Backward
#         client.publish(MQTT_TOPIC, "back") 
#     elif key.lower() == 'a':  # Left turn
#         client.publish(MQTT_TOPIC, "left")
#     elif key.lower() == 'd':  # Right turn
#         client.publish(MQTT_TOPIC, "right")
#     elif key.lower() == 'q':  # Quit
#         stop_listening()

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
    

def move_towards_bottle(frame_width, bottle_coords):
    """
    Determine movement direction based on bottle position in frame
    Returns a string indicating direction to move
    """
    global following_path
    
    if not bottle_coords:
        client.publish(MQTT_TOPIC_BOTTLE, json.dumps({
            "detected": False,
            "x": 0.0
        }))
        return "no_bottle"
    
    x1, y1, x2, y2 = bottle_coords
    bottle_center_x = (x1 + x2) // 2
    bottle_center_y = (y1 + y2) // 2
    
    # Calculate bottle size in frame (rough depth estimation)
    bottle_width = x2 - x1
    bottle_height = y2 - y1
    bottle_size = bottle_width * bottle_height
    
    # Publish bottle position and size information
    normalized_x = (bottle_center_x / frame_width * 2) - 1
    msg = {
        "detected": True,
        "x": normalized_x,
        "size": bottle_size,
        "frame_size": frame_width * frame_width
    }
    client.publish(MQTT_TOPIC_BOTTLE, json.dumps(msg))
    
    # Let path planning handle the navigation
    if not following_path:
        print("[yolo_custom.py] Waiting for path planning...")
    else:
        print("[yolo_custom.py] Following path")
    return "following_path"

def on_path_message(client, userdata, message):
    global following_path, current_path

    
    if message.topic == MQTT_TOPIC_PATH_PLAN:
        payload = json.loads(message.payload)
        current_path = payload.get("path_xy", [])
        following_path = True
        print("[yolo_custom.py] Received new path plan")
    
    elif message.topic == MQTT_TOPIC_PATH_COMPLETED:
        following_path = False
        current_path = None
        print("[yolo_custom.py] Path completed, waiting for new path")

# def get_bounding_boxes():
#     # Setup MQTT subscriptions
#     client.subscribe(MQTT_TOPIC_PATH_PLAN)

#     client.subscribe(MQTT_TOPIC_PATH_COMPLETED)
#     client.on_message = on_path_message

#     # Load your custom YOLO model
#     model = YOLO("best_bottle.pt", task="detect")  # Replace with your trained model path

#     # Open video stream (0 for webcam, or replace with video path)
#     video_path = 0  # Change this to "video.mp4" if using a file
#     cap = cv2.VideoCapture(video_path)
    
#     # Get frame width for movement calculations
#     frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

#     count = 0


#     while cap.isOpened():
#         ret, frame = cap.read()
#         if not ret:
#             break  # Exit if video ends

#         # Run YOLO inference
#         results = model(frame)
        
#         objects = [0, 0, 0]
#         bottle_coords = None

#         # Draw bounding boxes on the frame
#         for i in range(len(results)):
#             if (i > 3):
#                 break
#             result = results[i]
#             for box in result.boxes:
#                 x1, y1, x2, y2 = map(int, box.xyxy[0])  # Bounding box coordinates
#                 conf = box.conf[0]  # Confidence score
#                 cls = int(box.cls[0])  # Class index
                
#                 objects[i] = {"coords": [x1, y1, x2, y2], "conf": conf, "class": model.names[cls]}
#                 print(f"object{i}: confidence:", conf, "class:", model.names[cls])
                
#                 # Store coordinates if object is a bottle
#                 if model.names[cls].lower() == "bottle" and conf > 0.6:  # Added confidence threshold
#                     bottle_coords = [x1, y1, x2, y2]
#                     print(f"[yolo_custom.py] Bottle detected with confidence: {conf:.2f}")
                
#                 cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
#                 cv2.putText(frame, f"{model.names[cls]} {conf:.2f}", (x1, y1 - 10), 
#                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
#         # Get movement direction based on bottle position
#         # move_towards_bottle(frame_width, bottle_coords)
#         home_towards_bottle(bottle_coords)

#         if count % 10 == 0:
#             cv2.imwrite('img/img_' + str(count) + ".png", frame)
#         count += 1
#         cv2.imwrite('img.jpg', frame)
#         # print("Movement direction:", movement)
            
#         # cv2.imshow("YOLOv5 Object Detection", frame)
#         # Exit on 'q' key
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break

#     cap.release()
#     cv2.destroyAllWindows()

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
    
	
        cv2.imwrite('img.jpg', frame)
    # Get movement direction based on bottle position
    # move_towards_bottle(frame_width, bottle_coords)
    return bottle_coords



model = YOLO("best_bottle.pt", task="detect")  # Replace with your trained model path
#get_bounding_boxes(model)

vision = Vision()
while True:
    ret,frame = vision.get_frame()
    if not ret:
        break
    bottle_coords = get_bounding_boxes(frame, model)
    home_towards_bottle(bottle_coords)
