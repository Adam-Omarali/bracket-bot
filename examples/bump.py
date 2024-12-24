import paho.mqtt.client as mqtt
import json
import threading
from velocity_publisher import RobotController

if __name__ == "__main__":
    controller = RobotController(velocity_broker="localhost", orientation_broker="localhost", velocity=0.2)
    controller.publish_velocity(0.1, 0)
    
