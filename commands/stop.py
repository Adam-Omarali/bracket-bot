import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from examples.drive_controller import RobotController

def stop():
    controller = RobotController()
    controller.set_motor_speeds(0, 0)
    controller.stop_motors()

if __name__ == "__main__":
    stop()
