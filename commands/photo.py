#!/usr/bin/env python3

import cv2
import sys
import time
import os

# Constants
OUTPUT_FILE = "camera_feed"
CAPTURE_INTERVAL = 0.1  # 2 times per second

def main():
    # Initialize camera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        sys.exit(1)
    print("Camera initialized successfully")
    print(f"Capturing frames every {CAPTURE_INTERVAL} seconds")
    i = 0
    try:
        while True:
            # Capture frame
            ret, frame = cap.read()
            
            if not ret:
                print("Error: Could not grab frame from camera")
                break
                
            # Save the frame
            cv2.imwrite(OUTPUT_FILE + str(i) + ".png", frame)
            i += 1
            
            # Wait for next capture
            time.sleep(CAPTURE_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nStopping camera capture")
    finally:
        cap.release()
        print("Camera released")

if __name__ == "__main__":
    main()
