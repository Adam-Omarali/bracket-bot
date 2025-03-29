import time
from examples.drive_controller import RobotController

controller = RobotController()
controller.start_motors()
while True:
    print(controller.get_position())
    print(controller.get_velocity())
    time.sleep(0.1)
