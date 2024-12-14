import time
import os
from RPi import GPIO
import paho.mqtt.client as mqtt
from threading import Thread

# GPIO setup for servo control
GPIO.setmode(GPIO.BCM)
GPIO.setup(6, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
pwm1 = GPIO.PWM(6, 50)  # 50 Hz frequency for servos
pwm2 = GPIO.PWM(13, 50)  # Second servo

# Calculate duty cycles for angles:
# 90 degrees = 6.5% duty cycle
# 0 degrees = 2.5% duty cycle
error_duty = 6.5     # 90 degrees - legs out
ok_duty = 2.5       # 0 degrees - legs in

# Track current servo state to avoid unnecessary updates
current_state = None  # Start with no state
pwm_start_time = None  # Initialize PWM start time

class WatchdogSubscriber(Thread):
    def __init__(self, broker_address="localhost", topic="balance_watchdog"):
        super().__init__()
        self.broker_address = broker_address
        self.topic = topic
        self.last_timestamp = 0
        self.client = mqtt.Client()

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        client.subscribe(self.topic)

    def on_message(self, client, userdata, msg):
        try:
            self.last_timestamp = float(msg.payload.decode())
        except ValueError as e:
            print(f"Error decoding timestamp: {e}")

    def run(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.broker_address)
        self.client.loop_forever()

def set_servo_positions(duty_cycle):
    global current_state, pwm_start_time
    if current_state != duty_cycle:
        # Only change position if needed
        pwm1.start(duty_cycle)
        pwm2.start(duty_cycle)
        pwm_start_time = time.time()
        current_state = duty_cycle
        print(f"Set servos to {duty_cycle}%")

def check_watchdog(watchdog):
    current_time = time.time()
    if current_time - watchdog.last_timestamp > 0.1:
        set_servo_positions(error_duty)
    else:
        set_servo_positions(ok_duty)

# Initialize MQTT subscriber
watchdog = WatchdogSubscriber()
watchdog.start()

# Initial position
set_servo_positions(error_duty)

while True:
    check_watchdog(watchdog)
    # Stop the PWM after 1.5 seconds
    if pwm_start_time and time.time() - pwm_start_time >= 1.5:
        pwm1.stop()
        pwm2.stop()
        pwm_start_time = None  # Reset the start time
    time.sleep(0.05)  # Check every 50ms