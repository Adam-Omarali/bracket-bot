import cv2
import paho.mqtt.client as mqtt

MQTT_BROKER_ADDRESS = "localhost"
MQTT_TOPIC = "robot/frame"

class Vision:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Vision, cls).__new__(cls)
            cls._instance.cap = cv2.VideoCapture(0)
        return cls._instance

    def get_frame(self):
        return self.cap.read()
    
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
            client.publish(MQTT_TOPIC, frame)
        client.loop_stop()
        client.disconnect()
