import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from systems.Robot import RobotController

#run this file

if __name__ == "__main__":
    controller = RobotController()
    controller.move(desired_pos=1)