# Adds the lib directory to the Python path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import time
import json
import traceback
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
from threading import Event, Thread

import paho.mqtt.client as mqtt
from RPi import GPIO
from lib.imu import FilteredMPU6050
from lib.odrive_uart import ODriveUART, reset_odrive
from lib.lqr import LQR_gains

# GPIO setup for resetting ODrive
GPIO.setmode(GPIO.BCM)
GPIO.setup(5, GPIO.OUT)

# Constants from original file
WHEEL_RADIUS = 6.5 * 0.0254 / 2
WHEEL_DIST = 0.235
YAW_RATE_TO_MOTOR_TORQUE = (WHEEL_DIST / WHEEL_RADIUS) * 0.1
MOTOR_TURNS_TO_LINEAR_POS = WHEEL_RADIUS * 2 * np.pi
RPM_TO_METERS_PER_SECOND = WHEEL_RADIUS * 2 * np.pi / 60
MAX_TORQUE = 5.0
MAX_SPEED = 1.0


class MqttSubscriber(Thread):
    def __init__(self, broker_address="localhost", topic="robot/velocity"):
        super().__init__(daemon=True)
        self.broker_address = broker_address
        self.topic = topic
        self.desired_vel = 0
        self.desired_yaw_rate = 0
        self.client = mqtt.Client()
        self._stop_event = Event()

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        client.subscribe(self.topic)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            self.desired_vel = payload.get("linear", 0)
            self.desired_yaw_rate = payload.get("angular", 0)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")

    def stop(self):
        self._stop_event.set()
        self.client.disconnect()

    def run(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.broker_address)
        self.client.loop_start()
        self._stop_event.wait()  # Wait for stop event instead of sleeping
        self.client.loop_stop()


def balance():
    # Initialize keyboard thread
    mqtt_control = MqttSubscriber()
    mqtt_control.start()

    # Initialize MQTT client for watchdog
    watchdog_client = mqtt.Client()
    watchdog_client.connect("localhost")

    # Initialize IMU and LQR gains (same as original)
    imu = FilteredMPU6050()
    K_balance = LQR_gains(Q_diag=[100,10,100,1,10,1], R_diag=[0.2, 1])
    K_drive = LQR_gains(Q_diag=[1,100,1,1,1,10], R_diag=[0.2, 1])
    print(K_balance.round(2))
    Dt = 1./200.

    # Initialize variables
    zero_angle = 3.0
    start_plot_time = time.time()

    # Initialize plotting arrays (same as original)
    times, positions, desired_positions = [], [], []
    velocities, desired_velocities = [], []
    pitches, desired_pitches = [], []
    pitch_rates, desired_pitch_rates = [], []
    yaws, desired_yaws = [], []
    yaw_rates, desired_yaw_rates = [], []
    torques = deque(maxlen=200)

    # Reset ODrive and initialize motors
    reset_odrive()
    time.sleep(1)

    # Initialize motors (same as original)
    try:
        with open(os.path.expanduser('~/quickstart/lib/motor_dir.json'), 'r') as f:
            motor_dirs = json.load(f)
            left_dir = motor_dirs['left']
            right_dir = motor_dirs['right']
    except Exception as e:
        raise Exception("Error reading motor_dir.json")

    motor_controller = ODriveUART(port='/dev/ttyAMA1', left_axis=0, right_axis=1, dir_left=left_dir, dir_right=right_dir)
    motor_controller.clear_errors_left()
    motor_controller.clear_errors_right()
    motor_controller.start_left()
    motor_controller.enable_torque_mode_left()
    motor_controller.start_right()
    motor_controller.enable_torque_mode_right()
    motor_controller.set_speed_rpm_left(0)
    motor_controller.set_speed_rpm_right(0)

    def reset_and_initialize_motors():
        nonlocal motor_controller
        reset_odrive()
        time.sleep(1)  # Give ODrive time to reset
        try:
            motor_controller = ODriveUART(port='/dev/ttyAMA1', left_axis=0, right_axis=1, dir_left=left_dir, dir_right=right_dir)
            motor_controller.clear_errors_left()
            motor_controller.clear_errors_right()
            motor_controller.enable_torque_mode_left()
            motor_controller.enable_torque_mode_right()
            motor_controller.start_left()
            motor_controller.start_right()
            print("Motors re-initialized successfully.")
        except Exception as e:
            print(f"Error re-initializing motors: {e}")

    # Record starting position
    try:
        l_pos = motor_controller.get_position_turns_left()
        r_pos = motor_controller.get_position_turns_right()
        start_pos = (l_pos + r_pos) / 2 * MOTOR_TURNS_TO_LINEAR_POS
        start_yaw = (l_pos - r_pos) * MOTOR_TURNS_TO_LINEAR_POS / (2*WHEEL_DIST)
    except Exception as e:
        print(f"Error reading initial motor positions: {e}")
        return

    imu.calibrate()
    cycle_count = 0
    is_pos_control = True

    try:
        motor_controller.enable_watchdog_left()
        motor_controller.enable_watchdog_right()

        while True:
            loop_start_time = time.time()

            # Feed the watchdog
            watchdog_client.publish("balance_watchdog", str(time.time()))

            if cycle_count % 20 == 0:
                try:
                    if motor_controller.has_errors():
                        motor_controller.dump_errors()
                        reset_and_initialize_motors()
                        continue
                except Exception as e:
                    print('Error checking motor errors:', e)
                    reset_and_initialize_motors()
                    continue

            desired_pos = 0
            # Get desired velocity and yaw rate from keyboard thread
            desired_vel = mqtt_control.desired_vel
            desired_yaw_rate = mqtt_control.desired_yaw_rate
            # zero_angle += keyboard_control.zero_angle_adjustment

            was_pos_control = is_pos_control
            # is_pos_control = False
            is_pos_control = desired_vel == 0 and desired_yaw_rate == 0 and np.mean(np.abs([0]+velocities[-50:])) < 0.2
            if is_pos_control and not was_pos_control:
                start_pos = (l_pos + r_pos) / 2 * MOTOR_TURNS_TO_LINEAR_POS
            if desired_yaw_rate != 0:
                start_yaw = (l_pos - r_pos) * MOTOR_TURNS_TO_LINEAR_POS / (2*WHEEL_DIST)

            # Rest of the control loop (same as original)
            try:
                pitch, roll, yaw = imu.get_orientation()
            except:
                continue
            current_pitch = -pitch
            current_yaw_rate = -imu.gyro_RAW[2]
            current_pitch_rate = imu.gyro_RAW[0]


            try:
                l_pos, l_vel = motor_controller.get_pos_vel_left()
                r_pos, r_vel = motor_controller.get_pos_vel_right()
                current_vel = (l_vel + r_vel) / 2 * RPM_TO_METERS_PER_SECOND
                current_pos = (l_pos + r_pos) / 2 * MOTOR_TURNS_TO_LINEAR_POS - start_pos
                current_yaw = (l_pos - r_pos) * MOTOR_TURNS_TO_LINEAR_POS / (2*WHEEL_DIST) - start_yaw
            except Exception as e:
                print('Motor controller error:', e)
                reset_and_initialize_motors()
                continue

            if is_pos_control and abs(current_vel) < 0.01:
                zero_angle += 0.0002*np.sign(current_pitch-zero_angle)

            # Store data for plotting
            current_time = time.time()
            times.append(current_time - start_plot_time)
            positions.append(current_pos)
            desired_positions.append(desired_pos)
            velocities.append(current_vel)
            desired_velocities.append(desired_vel)
            pitches.append(current_pitch)
            desired_pitches.append(zero_angle)
            pitch_rates.append(current_pitch_rate)
            desired_pitch_rates.append(0)
            yaws.append(current_yaw)
            desired_yaws.append(0)
            yaw_rates.append(current_yaw_rate)
            desired_yaw_rates.append(desired_yaw_rate)

            # Calculate control outputs
            current_state = np.array([
                current_pos, current_vel, current_pitch*np.pi/180, 
                current_pitch_rate, current_yaw, current_yaw_rate
            ])
            
            desired_state = np.array([
                desired_pos, desired_vel, zero_angle*np.pi/180, 0, 0, desired_yaw_rate
            ])

            state_error = (current_state - desired_state).reshape((6,1))

            if is_pos_control:
                # Position control
                C = -K_balance @ state_error
            else:
                # Velocity control
                state_error[0,0] = 0
                state_error[4,0] = 0
                C = -K_drive @ state_error
            
                
            D = np.array([[0.5,0.5],[0.5,-0.5]])
            left_torque, right_torque = (D @ C).squeeze()

            # Limit torques
            left_torque = np.clip(left_torque, -MAX_TORQUE, MAX_TORQUE)
            right_torque = np.clip(right_torque, -MAX_TORQUE, MAX_TORQUE)
            torques.append((np.abs(left_torque) + np.abs(right_torque)/2))
            if len(torques) == 200 and np.all(np.array(torques) > 0.99*MAX_TORQUE):
                break

            # Apply torques
            try:
                motor_controller.set_torque_nm_left(left_torque)
                motor_controller.set_torque_nm_right(right_torque)
            except Exception as e:
                print('Motor controller error:', e)
                reset_and_initialize_motors()
                continue

            if cycle_count % 50 == 0:
                print(f"Loop time: {time.time() - loop_start_time:.6f} sec, u={(float(left_torque), float(right_torque))}, x=[{current_pos:.2f} | {desired_pos}], v=[{current_vel:.2f} | {desired_vel:.2f}], θ=[{current_pitch:.2f} | {zero_angle:.2f}], ω=[{current_pitch_rate:.2f} | 0], δ=[{current_yaw:.2f} | 0], δ'=[{current_yaw_rate:.2f} | {desired_yaw_rate:.2f}]")

            cycle_count += 1
            time.sleep(max(0, Dt - (time.time() - current_time)))

    except KeyboardInterrupt:
        print("Balance stopped by user.")

    except Exception as e:
        print("An error occurred:")
        traceback.print_exc()

    finally:
        # Cleanup
        mqtt_control.stop()
        motor_controller.disable_watchdog_left()
        motor_controller.disable_watchdog_right()
        motor_controller.stop_left()
        motor_controller.stop_right()
        motor_controller.clear_errors_left()
        motor_controller.clear_errors_right()

        # Create the plots
        fig, ((ax1, ax2), (ax3, ax4), (ax5, ax6)) = plt.subplots(3, 2, figsize=(15, 12))
        
        # Plot positions (x)
        ax1.plot(times, positions, label='Current Position')
        ax1.plot(times, desired_positions, label='Desired Position')
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Position (m)')
        ax1.legend()
        ax1.grid(True)
        ax1.set_title('Position')
        
        # Plot velocities (v)
        ax2.plot(times, velocities, label='Current Velocity')
        ax2.plot(times, desired_velocities, label='Desired Velocity')
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Velocity (m/s)')
        ax2.legend()
        ax2.grid(True)
        ax2.set_title('Velocity')

        # Plot pitches
        ax3.plot(times, pitches, label='Current Pitch')
        ax3.plot(times, desired_pitches, label='Desired Pitch')
        ax3.set_xlabel('Time (s)')
        ax3.set_ylabel('Pitch (deg)')
        ax3.legend()
        ax3.grid(True)
        ax3.set_title('Pitch')

        # Plot pitch rates
        ax4.plot(times, pitch_rates, label='Current Pitch Rate')
        ax4.plot(times, desired_pitch_rates, label='Desired Pitch Rate')
        ax4.set_xlabel('Time (s)')
        ax4.set_ylabel('Pitch Rate (rad/s)')
        ax4.legend()
        ax4.grid(True)
        ax4.set_title('Pitch Rate')
        ax4.yaxis.set_major_locator(plt.MultipleLocator(np.pi/2))
        ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/np.pi:.1f}π'))

        # Plot yaws
        ax5.plot(times, yaws, label='Current Yaw')
        ax5.plot(times, desired_yaws, label='Desired Yaw')
        ax5.set_xlabel('Time (s)')
        ax5.set_ylabel('Yaw (rad)')
        ax5.legend()
        ax5.grid(True)
        ax5.set_title('Yaw')
        ax5.yaxis.set_major_locator(plt.MultipleLocator(np.pi/2))
        ax5.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/np.pi:.1f}π'))

        # Plot yaw rates
        ax6.plot(times, yaw_rates, label='Current Yaw Rate')
        ax6.plot(times, desired_yaw_rates, label='Desired Yaw Rate')
        ax6.set_xlabel('Time (s)')
        ax6.set_ylabel('Yaw Rate (rad/s)')
        ax6.legend()
        ax6.grid(True)
        ax6.set_title('Yaw Rate')
        ax6.yaxis.set_major_locator(plt.MultipleLocator(np.pi/2))
        ax6.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/np.pi:.1f}π'))

        plt.tight_layout()
        plt.savefig('plots.png')
        os.system('cursor plots.png')

if __name__ == "__main__":
    balance()
