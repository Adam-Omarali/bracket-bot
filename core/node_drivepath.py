#!/usr/bin/env python3

import json
import time
import math
import paho.mqtt.client as mqtt

MQTT_BROKER             = "localhost"
MQTT_PORT               = 1883
MQTT_TOPIC_PATH_PLAN    = "robot/local_path"
MQTT_TOPIC_DRIVE_CMD    = "robot/drive"
MQTT_TOPIC_ODOMETRY     = "robot/odometry"
MQTT_TOPIC_PATH_DONE    = "robot/path_complete"

MAX_LINEAR_SPEED   = 0.1
MAX_ANGULAR_SPEED  = 0.5
K_LINEAR           = 1.0
K_ANGULAR          = 0.5
K_ANGULAR_DRIVE    = 0.2
ANGLE_THRESHOLD    = 0.2    # ~11.5 deg
DISTANCE_THRESHOLD = 0.1    # 10 cm

path_xy       = []
current_index = 0
robot_x       = 0.0
robot_y       = 0.0
robot_th      = 0.0  # Radians
state         = 'IDLE'

def wrap_angle(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi

def on_message(client, userdata, msg):
    if msg.topic == MQTT_TOPIC_PATH_PLAN:
        on_path_plan(msg)
    elif msg.topic == MQTT_TOPIC_ODOMETRY:
        on_odometry(msg)

def on_path_plan(msg):
    global path_xy, current_index, state
    data = json.loads(msg.payload)

    print("data", data)
    new_path = data.get('path_xy', [])
    print("new_path", new_path)
    path_xy  = new_path
    current_index = 0
    if path_xy:
        state = 'ROTATING'
        print(f"[node_drivepath.py] New path with {len(path_xy)} waypoints => starting from 0")
    else:
        state = 'IDLE'

def on_odometry(msg):
    global robot_x, robot_y, robot_th
    data = json.loads(msg.payload)
    robot_x  = data.get('x', robot_x)
    robot_y  = data.get('y', robot_y)
    robot_th = data.get('theta', 0.0)  # radians

def main():
    global path_xy, current_index, state
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.subscribe(MQTT_TOPIC_PATH_PLAN)
    client.subscribe(MQTT_TOPIC_ODOMETRY)
    client.loop_start()

    try:
        while True:
            time.sleep(0.1)

            # Print the robot's position
            # print(f"Robot position - X: {robot_x}, Y: {robot_y}, Theta: {robot_th}")

            if not path_xy or state == 'IDLE':
                # Send zero command
                cmd = {'linear_velocity': 0.0, 'angular_velocity': 0.0}
                client.publish(MQTT_TOPIC_DRIVE_CMD, json.dumps(cmd))
                continue

            if current_index >= len(path_xy):
                # Path completed
                print("[node_drivepath.py] Path done => sending path_completed.")
                client.publish(MQTT_TOPIC_PATH_DONE, json.dumps({'status': 'completed'}))
                path_xy = []
                state = 'IDLE'
                continue

            gx, gy = path_xy[current_index]
            dx = gx - robot_x
            dy = gy - robot_y
            dist = math.hypot(dx, dy)

            angle_to_goal = math.atan2(dy, dx)
            angle_error   = wrap_angle(angle_to_goal - robot_th)

            # Check if we are within threshold
            if dist < DISTANCE_THRESHOLD:
                current_index += 1
                if current_index < len(path_xy):
                    state = 'ROTATING'
                else:
                    # Next iteration we'll do PATH_DONE
                    pass
                continue
            print("state", state)
            state = 'DRIVING'
            if state == 'ROTATING':
                print("angle_error", angle_error, "angle_threshold", ANGLE_THRESHOLD)
                if abs(angle_error) < ANGLE_THRESHOLD:
                    state = 'DRIVING'
                else:
                    # Rotate in place
                    print("rotating in place")
                    ang_vel = K_ANGULAR * angle_error
                    ang_vel = max(-MAX_ANGULAR_SPEED, min(MAX_ANGULAR_SPEED, ang_vel))
                    cmd = {'linear_velocity': 0.0, 'angular_velocity': ang_vel}
                    client.publish(MQTT_TOPIC_DRIVE_CMD, json.dumps(cmd))

            elif state == 'DRIVING':
                
                lin_vel = K_LINEAR * dist
                lin_vel = min(lin_vel, MAX_LINEAR_SPEED)
                ang_vel = K_ANGULAR_DRIVE * angle_error
                ang_vel = max(-MAX_ANGULAR_SPEED, min(MAX_ANGULAR_SPEED, ang_vel))
                
                # print(f"Robot position - X: {robot_x}, Y: {robot_y}, Theta: {robot_th}")

                cmd = {
                    'linear_velocity': lin_vel,
                    'angular_velocity': ang_vel
                }
                
                
                client.publish(MQTT_TOPIC_DRIVE_CMD, json.dumps(cmd))

    except KeyboardInterrupt:
        print("\n[node_drivepath.py] Interrupted.")
    finally:
        cmd_msg = {'linear_velocity': 0.0, 'angular_velocity': 0.0}
        client.publish(MQTT_TOPIC_DRIVE_CMD, json.dumps(cmd_msg))
        client.loop_stop()
        client.disconnect()
        print("[node_drivepath.py] Shutdown complete.")

if __name__ == "__main__":
    main()
