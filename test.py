from lib.odrive_uart import ODriveUART, reset_odrive
from lib.imu import FilteredMPU6050
import time
import os
import json

imu = FilteredMPU6050()

reset_odrive()  # Reset ODrive before initializing motors
time.sleep(1)   # Wait for ODrive to reset

# Initialize motors
# Read motor directions from saved file
try:
    with open(os.path.expanduser('~/quickstart/lib/motor_dir.json'), 'r') as f:
        motor_dirs = json.load(f)
        left_dir = motor_dirs['left']
        right_dir = motor_dirs['right']
except Exception as e:
    raise Exception("Error reading motor_dir.json")

motor_controller = ODriveUART(port='/dev/ttyAMA1', left_axis=0, right_axis=1, dir_left=left_dir, dir_right=right_dir)
motor_controller.start_left()
motor_controller.enable_torque_mode_left()
motor_controller.start_right()
motor_controller.enable_torque_mode_right()
motor_controller.set_speed_rpm_left(0)
motor_controller.set_speed_rpm_right(0)