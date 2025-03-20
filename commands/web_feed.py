import cv2
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import numpy as np
from ultralytics import YOLO
import yolo_custom
import sys
import os
import threading
import queue
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from subsystem.Vision import Vision

model = YOLO("../lib/cv/yolo/best_bottle.pt")
vision = Vision()

# Open the camera (adjust the index if needed)
# camera = cv2.VideoCapture('/dev/video0')

# Define the list of class labels MobileNet SSD was trained to detect.
CLASSES = ["bottle"]

class FrameProcessor:
    def __init__(self):
        print("Initializing FrameProcessor...")
        self.frame_queue = queue.Queue(maxsize=2)
        self.processed_frame_queue = queue.Queue(maxsize=2)
        self.running = True
        self.start_processing_thread()
        print("FrameProcessor initialized successfully")

    def start_processing_thread(self):
        self.process_thread = threading.Thread(target=self.process_frames)
        self.process_thread.daemon = True
        self.process_thread.start()

    def process_frames(self):
        print("Processing thread started")
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=1)
                print("Processing new frame")
                # Process frame with YOLO
                bottle_coords = yolo_custom.get_bounding_boxes(frame, model)
                yolo_custom.home_towards_bottle(bottle_coords)
                
                # Put processed frame in output queue
                if self.processed_frame_queue.full():
                    self.processed_frame_queue.get()
                self.processed_frame_queue.put((frame, bottle_coords))
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in process_frames: {str(e)}")

    def stop(self):
        self.running = False
        if self.process_thread.is_alive():
            self.process_thread.join()

# Create global frame processor
frame_processor = FrameProcessor()

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            # Serve a simple HTML page that displays the camera feed
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>Camera Feed</title>
    <style>
        body { text-align: center; font-family: Arial, sans-serif; }
    </style>
</head>
<body>
    <h1>Live Camera Feed</h1>
    <img src="/video_feed" width="640" height="480" alt="Camera Feed">
</body>
</html>
'''
            self.wfile.write(html_content.encode('utf-8'))
        elif self.path == '/video_feed':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            try:
                while True:
                    ret, frame = vision.get_frame()
                    if not ret:
                        continue

                    # Add frame to processing queue
                    if not frame_processor.frame_queue.full():
                        frame_processor.frame_queue.put(frame)
                    
                    ret, jpeg = cv2.imencode('.jpg', frame)
                    if not ret:
                        continue
                    
                    self.wfile.write(b'--frame\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(b'Content-Length: ' + str(len(jpeg.tobytes())).encode() + b'\r\n')
                    self.wfile.write(b'\r\n')
                    self.wfile.write(jpeg.tobytes())
                    self.wfile.write(b'\r\n')
                    time.sleep(0.05)  # Adjust delay to control frame rate
            except Exception as e:
                print("Streaming client disconnected: ", str(e))
        else:
            self.send_error(404, 'File Not Found: %s' % self.path)

def run(server_class=HTTPServer, handler_class=MyHandler, port=8080):
    print("Starting server...")
    try:
        print("Starting server initialization...")
        server_address = ('', port)
        print(f"Creating HTTP server on port {port}...")
        httpd = server_class(server_address, handler_class)
        print(f"Serving camera feed on port {port}...")
        httpd.serve_forever()
    except Exception as e:
        print(f"Error starting server: {str(e)}")
    finally:
        print("Cleaning up...")
        frame_processor.stop()  # Clean up when server stops

if __name__ == '__main__':
    run()
