import cv2
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import numpy as np
import sys
import os
from ultralytics import YOLO

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from subsystem.Vision import RealsenseVision

vision = RealsenseVision()
model = YOLO('lib/cv/yolo/yolo11n.pt', task='detect')

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            # Serve HTML page
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>Camera Feed</title>
    <script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>
    <style>
        body { 
            text-align: center; 
            font-family: Arial, sans-serif; 
        }
        .container {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 20px;
        }
        .button {
            display: inline-block;
            padding: 10px 20px;
            margin: 20px;
            background-color: #4CAF50;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            border: none;
        }
        .button:hover {
            background-color: #45a049;
        }
        .command-form {
            margin-top: 20px;
        }
        .text-input {
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-right: 10px;
            width: 300px;
        }
        #command-response {
            display: inline-block;
            margin-left: 10px;
            color: #4CAF50;
            font-weight: bold;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
        }
        
        #command-response.show {
            opacity: 1;
        }
    </style>
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // Extract hostname and setup MQTT like in node_web.py
        const hostname = window.location.hostname;
        const username = hostname.split('-')[0];
        const mqttHost = username.includes('.') ? hostname : `${username}-desktop.local`;
        const client = mqtt.connect(`ws://${mqttHost}:9001`);
        
        // Setup MQTT connection status
        client.on('connect', function () {
            document.getElementById('status').style.color = 'green';
            document.getElementById('status').innerHTML = 'Connected';
        });

        client.on('error', function (error) {
            document.getElementById('status').style.color = 'red';
            document.getElementById('status').innerHTML = 'Connection failed: ' + error;
        });

        // Handle form submission
        const form = document.querySelector('.command-form');
        const responseDiv = document.getElementById('command-response');
        
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const command = form.querySelector('input[name="command"]').value;
            
            // Publish command via MQTT
            client.publish("robot/command", command);
            
            // Show feedback message
            responseDiv.textContent = 'Command sent';
            responseDiv.classList.add('show');
            
            // Hide message after 3 seconds
            setTimeout(() => {
                responseDiv.classList.remove('show');
            }, 3000);
            
            form.reset();
        });
    });
    </script>
</head>
<body>
    <h1>Live Camera Feed</h1>
    <div id="status">Disconnected</div>
    <div class="container">
        <img src="/video_feed/combined" width="1280" height="480" alt="Combined Feed">
    </div>
    <div class="container">
        <form class="command-form">
            <input type="text" name="command" class="text-input" placeholder="Enter command...">
            <button type="submit" class="button">Submit Command</button>
            <span id="command-response"></span>
        </form>
    </div>
</body>
</html>'''
            self.wfile.write(html_content.encode('utf-8'))
            
        elif self.path == '/video_feed/combined':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            try:
                while True:
                    color_frame = vision.get_frame('color')
                    depth_frame = vision.get_frame('depth')
                    if color_frame is None or depth_frame is None:
                        continue

                    combined_frame = np.hstack((color_frame, depth_frame))
                    success, jpeg = cv2.imencode('.jpg', combined_frame)
                    if not success:
                        continue

                    self.wfile.write(b'--frame\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(b'Content-Length: ' + str(len(jpeg.tobytes())).encode() + b'\r\n')
                    self.wfile.write(b'\r\n')
                    self.wfile.write(jpeg.tobytes())
                    self.wfile.write(b'\r\n')
                    time.sleep(0.05)
            except Exception as e:
                print(f"Combined stream error: {str(e)}")
                
        elif self.path == '/video_feed/yolo':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            try:
                while True:
                    color_frame = vision.get_frame('color')
                    if color_frame is None:
                        continue
                    
                    results = vision.detect_objects(model, frame)
                    if results is None:
                        continue
                        
                    annotated_frame = vision.draw_bounding_boxes(color_frame, results, model)
                    if annotated_frame is None:
                        continue
                    
                    success, jpeg = cv2.imencode('.jpg', annotated_frame)
                    if not success:
                        continue

                    self.wfile.write(b'--frame\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(b'Content-Length: ' + str(len(jpeg.tobytes())).encode() + b'\r\n')
                    self.wfile.write(b'\r\n')
                    self.wfile.write(jpeg.tobytes())
                    self.wfile.write(b'\r\n')
                    time.sleep(0.05)
            except Exception as e:
                print(f"YOLO stream error: {str(e)}")
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

if __name__ == '__main__':
    run()
