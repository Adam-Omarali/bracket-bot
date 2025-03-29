import sys
import os
import json
import time
import math
import numpy as np
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.odrive_uart import ODriveUART
from lib.imu import FilteredMPU6050

class RobotState:
    # Robot physical constants
    WHEEL_DIAMETER_MM = 165  # Wheel diameter in millimeters
    WHEEL_BASE_MM = 400     # Distance between wheels in millimeters

    def __init__(self):
        # Initialize IMU
        self.imu = FilteredMPU6050()
        self.imu.calibrate()
        
        # Initialize ODrive
        try:
            with open(os.path.expanduser('~/quickstart/lib/motor_dir.json'), 'r') as f:
                motor_dirs = json.load(f)
                left_dir = motor_dirs['left']
                right_dir = motor_dirs['right']
        except Exception as e:
            print(f"Error reading motor_dir.json: {e}")
            left_dir = 1
            right_dir = 1
            
        self.odrive = ODriveUART(
            port='/dev/ttyAMA1', 
            left_axis=0, 
            right_axis=1, 
            dir_left=left_dir, 
            dir_right=right_dir
        )

        # Initialize IMU-based position tracking
        self.imu_pos = {'x': 0.0, 'y': 0.0}
        self.last_velocity = {'x': 0.0, 'y': 0.0}
        
        # Initialize wheel odometry position tracking
        self.wheel_pos = {'x': 0.0, 'y': 0.0}
        self.last_left_pos = 0.0
        self.last_right_pos = 0.0
        
        self.last_update_time = time.monotonic()

    def rpm_to_mps(self, rpm):
        """Convert RPM to meters per second"""
        wheel_circumference_m = (self.WHEEL_DIAMETER_MM / 1000) * math.pi
        rps = rpm / 60  # Convert RPM to revolutions per second
        return rps * wheel_circumference_m

    def turns_to_meters(self, turns):
        """Convert wheel turns to meters traveled"""
        wheel_circumference_m = (self.WHEEL_DIAMETER_MM / 1000) * math.pi
        return turns * wheel_circumference_m

    def update_imu_position(self, accel, yaw_deg, dt):
        """Update position using IMU data"""
        # Convert yaw to radians
        yaw_rad = math.radians(yaw_deg)
        
        # Rotate acceleration from IMU frame to world frame
        ax = accel[0] * math.cos(yaw_rad) - accel[1] * math.sin(yaw_rad)
        ay = accel[0] * math.sin(yaw_rad) + accel[1] * math.cos(yaw_rad)
        
        # Integrate acceleration to get velocity
        vx = self.last_velocity['x'] + ax * dt
        vy = self.last_velocity['y'] + ay * dt
        
        # Integrate velocity to get position
        self.imu_pos['x'] += (self.last_velocity['x'] + vx) * dt / 2
        self.imu_pos['y'] += (self.last_velocity['y'] + vy) * dt / 2
        
        # Update velocities for next iteration
        self.last_velocity = {'x': vx, 'y': vy}

    def update_wheel_position(self, left_pos, right_pos, yaw_deg):
        """Update position based on wheel rotations"""
        # Convert wheel positions to meters
        left_dist = self.turns_to_meters(left_pos - self.last_left_pos)
        right_dist = self.turns_to_meters(right_pos - self.last_right_pos)
        
        # Calculate average distance traveled
        dist = (left_dist + right_dist) / 2.0
        
        # Convert yaw to radians
        yaw_rad = math.radians(yaw_deg)
        
        # Update position
        self.wheel_pos['x'] += dist * math.cos(yaw_rad)
        self.wheel_pos['y'] += dist * math.sin(yaw_rad)
        
        # Store current positions for next update
        self.last_left_pos = left_pos
        self.last_right_pos = right_pos

    def get_state(self):
        """
        Get current robot state
        Returns:
            dict: {
                'position': {
                    'imu': {'x': float, 'y': float},    # IMU-based position in meters
                    'wheel': {'x': float, 'y': float}   # Wheel odometry position in meters
                },
                'velocity': {
                    'left': float,  # Left wheel velocity in m/s
                    'right': float  # Right wheel velocity in m/s
                },
                'orientation': {
                    'pitch': float, # Pitch angle in degrees
                    'roll': float,  # Roll angle in degrees
                    'yaw': float    # Yaw angle in degrees
                }
            }
        """
        try:
            # Get wheel data
            left_pos, left_vel_rpm = self.odrive.get_pos_vel_left()
            right_pos, right_vel_rpm = self.odrive.get_pos_vel_right()
            
            # Convert velocities from RPM to m/s
            left_vel_mps = self.rpm_to_mps(left_vel_rpm)
            right_vel_mps = self.rpm_to_mps(right_vel_rpm)
            
            # Get IMU data
            accel = self.imu.accel
            pitch, roll, yaw = self.imu.get_orientation()
            
            # Update position tracking
            current_time = time.monotonic()
            dt = current_time - self.last_update_time
            
            # Update both position estimates
            self.update_imu_position(accel, yaw, dt)
            self.update_wheel_position(left_pos, right_pos, yaw)
            
            self.last_update_time = current_time
            
            return {
                'position': {
                    'imu': self.imu_pos.copy(),
                    'wheel': self.wheel_pos.copy()
                },
                'velocity': {
                    'left': left_vel_mps,
                    'right': right_vel_mps
                },
                'orientation': {
                    'pitch': pitch,
                    'roll': roll,
                    'yaw': yaw
                }
            }
        except Exception as e:
            print(f"Error getting robot state: {e}")
            return None

if __name__ == '__main__':
    # Test the state monitoring
    robot = RobotState()
    
    try:
        while True:
            state = robot.get_state()
            if state:
                print("\nRobot State:")
                print("IMU Position (m) - " +
                      f"X: {state['position']['imu']['x']:.3f}, " +
                      f"Y: {state['position']['imu']['y']:.3f}")
                print("Wheel Position (m) - " +
                      f"X: {state['position']['wheel']['x']:.3f}, " +
                      f"Y: {state['position']['wheel']['y']:.3f}")
                print(f"Velocity (m/s) - Left: {state['velocity']['left']:.2f}, " +
                      f"Right: {state['velocity']['right']:.2f}")
                print(f"Orientation (deg) - Pitch: {state['orientation']['pitch']:.2f}, " +
                      f"Roll: {state['orientation']['roll']:.2f}, " +
                      f"Yaw: {state['orientation']['yaw']:.2f}")

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping state monitor...") 