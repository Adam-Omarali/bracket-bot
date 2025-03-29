import cv2
import paho.mqtt.client as mqtt
import pyrealsense2 as rs
import numpy as np
import threading
import time

MQTT_BROKER_ADDRESS = "localhost"
MQTT_TOPIC_DEPTH = "robot/frame/depth"
MQTT_TOPIC_COLOR = "robot/frame/color"
MQTT_TOPIC_YOLO = "robot/frame/yolo"

class WebcamVision:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebcamVision, cls).__new__(cls)
            cls._instance.cap = cv2.VideoCapture(0)
        return cls._instance

    def get_frame(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        return ret, frame
    
    def close(self):
        if hasattr(self, 'cap'):
            self.cap.release()
            Vision._instance = None

    def __del__(self):
        self.close()
        
    def stream_frames(self):
        client = mqtt.Client()
        client.connect(MQTT_BROKER_ADDRESS, 1883, 60)
        client.loop_start()
        while True:
            ret, frame = self.get_frame()
            if not ret:
                break
            client.publish(MQTT_TOPIC_DEPTH, frame)
        client.loop_stop()
        client.disconnect()


class RealsenseVision:
    _instance = None
    _running = False
    _thread = None
    _current_frames = {'depth': None, 'color': None}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RealsenseVision, cls).__new__(cls)
            try:
                # Initialize RealSense
                cls._instance.pipeline = rs.pipeline()
                cls._instance.config = rs.config()
                cls._instance.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
                cls._instance.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
                cls._instance.pipeline.start(cls._instance.config)
                
                # Initialize MQTT
                cls._instance.client = mqtt.Client()
                cls._instance.client.on_message = cls._instance._on_message
                cls._instance.client.connect(MQTT_BROKER_ADDRESS, 1883, 60)
                cls._instance.client.subscribe([
                    (MQTT_TOPIC_DEPTH, 0),
                    (MQTT_TOPIC_COLOR, 0)
                ])
                cls._instance.client.loop_start()
                
                # Start publishing frames
                cls._instance._start_publishing()
            except Exception as e:
                print(f"Error initializing RealSense camera: {str(e)}")
                return None
        return cls._instance

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            # Convert received bytes back to image
            nparr = np.frombuffer(msg.payload, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if msg.topic == MQTT_TOPIC_DEPTH:
                self._current_frames['depth'] = frame
            elif msg.topic == MQTT_TOPIC_COLOR:
                self._current_frames['color'] = frame
        except Exception as e:
            print(f"Error processing MQTT message: {str(e)}")

    def get_frame(self, frame_type='color'):
        """Get the most recent frame of the specified type"""
        return self._current_frames.get(frame_type)

    def get_frames(self):
        """Get both color and depth frames"""
        return self._current_frames['color'], self._current_frames['depth']

    def _start_publishing(self):
        """Start the frame publishing thread"""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._publish_frames)
            self._thread.daemon = True
            self._thread.start()
            print("Frame publishing started")

    def _publish_frames(self):
        """Thread function that continuously publishes frames"""
        while self._running:
            try:
                frames = self.pipeline.wait_for_frames()
                depth_frame = frames.get_depth_frame()
                color_frame = frames.get_color_frame()
                
                if not depth_frame or not color_frame:
                    continue
                
                # Convert frames to numpy arrays
                depth_image = np.asanyarray(depth_frame.get_data())
                color_image = np.asanyarray(color_frame.get_data())
                
                # Colormap the depth frame for visualization
                depth_colormap = cv2.applyColorMap(
                    cv2.convertScaleAbs(depth_image, alpha=0.03), 
                    cv2.COLORMAP_JET
                )
                
                # Rotate both images 90 degrees clockwise
                depth_colormap = cv2.rotate(depth_colormap, cv2.ROTATE_90_CLOCKWISE)
                color_image = cv2.rotate(color_image, cv2.ROTATE_90_CLOCKWISE)
                
                # Encode frames as JPEG
                _, depth_encoded = cv2.imencode('.jpg', depth_colormap)
                _, color_encoded = cv2.imencode('.jpg', color_image)
                
                # Publish frames
                self.client.publish(MQTT_TOPIC_DEPTH, depth_encoded.tobytes())
                self.client.publish(MQTT_TOPIC_COLOR, color_encoded.tobytes())
                
                time.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                print(f"Error publishing frames: {str(e)}")

    def close(self):
        """Stop publishing and clean up"""
        self._running = False
        if self._thread:
            self._thread.join()
        if hasattr(self, 'client'):
            self.client.loop_stop()
            self.client.disconnect()
        if hasattr(self, 'pipeline'):
            self.pipeline.stop()
        RealsenseVision._instance = None

    def __del__(self):
        self.close()

    def detect_objects(self, model, frame=None):
        """Run YOLO detection on a given frame and return the results"""
        try:
            # Run YOLO inference
            if frame is None:
                frame = self.get_frame('color')
            results = model(frame)
            return results
            
        except Exception as e:
            print(f"Error in detect_objects: {str(e)}")
            return None

    def draw_bounding_boxes(self, frame, results, model):
        """Draw bounding boxes on a frame based on YOLO results"""
        try:
            # Create a copy of the frame to draw on
            annotated_frame = frame.copy()
            
            # Draw bounding boxes on the frame
            for i in range(len(results)):
                result = results[i]
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])  # Bounding box coordinates
                    conf = box.conf[0]  # Confidence score
                    cls = int(box.cls[0])  # Class index
                    
                    print(f"object{i}: confidence:", conf, "class:", model.names[cls])
                    
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(annotated_frame, f"{model.names[cls]} {conf:.2f}", 
                              (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Encode and publish the annotated frame
            _, encoded_frame = cv2.imencode('.jpg', annotated_frame)
            self.client.publish(MQTT_TOPIC_YOLO, encoded_frame.tobytes())
            
            return annotated_frame
            
        except Exception as e:
            print(f"Error in draw_bounding_boxes: {str(e)}")
            return frame    