import paho.mqtt.client as mqtt  
import json  
import threading
import time  
import matplotlib.pyplot as plt
from multiprocessing import Process
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from commands.state import RobotState
from examples.drive_controller import RobotController
#run this file in parallel with lqr_balance_pubsub.py

def bump():
    Dt = 1. / 200. 
    THRESHOLD = 0.2
    desired_velocity = 0.5  
    window_size = 100
    stabilization_time = 1.0  # Ignore velocity error for 1 second
    velocity_err = []
    t = []
    t2 = []
    t3 = []
    t4 = []
    velocity_err_rates = []
    acceleration_err_rates = []
    controller = RobotController()
    state_provider = RobotState()
    controller.start_motors()
    controller.set_motor_speeds(desired_velocity, desired_velocity)
    last_change_time = time.time()
    last_desired_velocity = desired_velocity

    try:
        while True:
            current_time = time.time()
            state = state_provider.get_state()
            velocity = state['velocity']['left']

            if desired_velocity != last_desired_velocity:
                last_change_time = current_time
                last_desired_velocity = desired_velocity

            last_desired_velocity = desired_velocity

            if time.time() - last_change_time > stabilization_time:
                velocity_err.append(velocity - desired_velocity)
                t.append(current_time)
                if desired_velocity != 0:
                    if len(velocity_err) > window_size:
                        velocity_err_rate = sum(velocity_err[-window_size:]) / window_size
                        velocity_err_rates.append(velocity_err_rate)
                        #take the derivative of velocity error rates over 50 samples
                        if len(velocity_err_rates) > window_size:
                            derivatives = [(velocity_err_rates[i] - velocity_err_rates[i-1])/Dt for i in range(-window_size, -1)]
                            acceleration_err_rate = sum(derivatives) / len(derivatives)
                            acceleration_err_rates.append(acceleration_err_rate)
                            t4.append(current_time)
                        t2.append(current_time)  # Corrected typo
                        if abs(velocity_err_rate) > THRESHOLD and velocity_err_rate * last_desired_velocity < 0 and abs(acceleration_err_rate) > THRESHOLD: #make this as a function of velocity
                            #lower the threshold and change the velocity rate 
                            print(f"Bumped at time {current_time:.2f}")
                            controller.set_motor_speeds(-desired_velocity, -desired_velocity)
                            last_change_time = current_time
                            last_desired_velocity = -desired_velocity

                time.sleep(max(0, Dt - (time.time() - current_time)))
    except KeyboardInterrupt:
        pass
    
    finally:
        plt.figure()
        plt.plot(t, velocity_err)
        plt.savefig("velocity_err.png")

        plt.figure()
        plt.plot(t2, velocity_err_rates)  # Ensure this matches the variable name
        plt.savefig("velocity_err_rate.png")

        plt.figure()
        plt.plot(t4, acceleration_err_rates)
        plt.savefig("acceleration_err_rate.png")

        controller.stop_motors()

if __name__ == "__main__":
    bump()
    
