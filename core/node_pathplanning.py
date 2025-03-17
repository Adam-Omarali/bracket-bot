
#!/usr/bin/env python3

import json
import time
import math
import random
import numpy as np
import paho.mqtt.client as mqtt
from heapq import heappush, heappop

# -----------------------------------------------------------------------------
# MQTT Setup
# -----------------------------------------------------------------------------
MQTT_BROKER = "localhost"
MQTT_PORT   = 1883

# Topics
MQTT_TOPIC_OCC_GRID       = "robot/tof_map"
MQTT_TOPIC_PATH_PLAN      = "robot/local_path"
MQTT_TOPIC_PATH_COMPLETED = "robot/path_completed"
MQTT_TOPIC_ODOMETRY       = "robot/odometry"
MQTT_TOPIC_BOTTLE         = "robot/bottle_position"

client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
client.loop_start()

# Global
occupancy_grid = None
grid_params    = {}
current_path   = None
need_new_path  = True
robot_x        = 0.0
robot_y        = 0.0
robot_th_deg   = 0.0
bottle_detected = False
bottle_x_norm = 0.0  # Normalized bottle x position (-1 to 1)
MIN_DISTANCE = 0.4  # Minimum approach distance in meters
MAX_DISTANCE = 1.2  # Maximum approach distance in meters
BOTTLE_SIZE_THRESHOLD = 0.4  # Bottle size relative to frame to stop approaching

# -----------------------------------------------------------------------------
# MQTT Callbacks
# -----------------------------------------------------------------------------
def on_message(client, userdata, message):
    if message.topic == MQTT_TOPIC_OCC_GRID:
        on_occupancy_grid(message)
    elif message.topic == MQTT_TOPIC_PATH_COMPLETED:
        on_path_completed(message)
    elif message.topic == MQTT_TOPIC_ODOMETRY:
        on_odometry(message)
    elif message.topic == MQTT_TOPIC_BOTTLE:
        on_bottle_detection(message)

def on_occupancy_grid(message):
    global occupancy_grid, grid_params
    payload = json.loads(message.payload)
    if "occupancy_grid" not in payload:
        return
    grid_info = payload["occupancy_grid"]
    data_flat = grid_info["data"]
    h = grid_info["height"]
    w = grid_info["width"]
    occupancy_grid = np.array(data_flat, dtype=np.uint8).reshape((h, w))

    grid_params = {
        "height":     h,
        "width":      w,
        "resolution": grid_info["resolution"],
        "min_x":      grid_info["min_x"],
        "max_x":      grid_info["max_x"],
        "min_y":      grid_info["min_y"],
        "max_y":      grid_info["max_y"]
    }

def on_path_completed(message):
    global need_new_path
    print("[node_pathplanning.py] Path completed => need_new_path = True")
    need_new_path = True

def on_odometry(message):
    global robot_x, robot_y, robot_th_deg
    payload = json.loads(message.payload)
    robot_x  = payload.get('x', robot_x)
    robot_y  = payload.get('y', robot_y)
    robot_th = payload.get('theta', 0.0)  # radians
    robot_th_deg = math.degrees(robot_th)

def on_bottle_detection(message):
    global bottle_detected, bottle_x_norm, need_new_path
    payload = json.loads(message.payload)
    bottle_detected = payload.get("detected", False)
    bottle_x_norm = payload.get("x", 0.0)
    need_new_path = True

# -----------------------------------------------------------------------------
# Subscribe
# -----------------------------------------------------------------------------
client.subscribe(MQTT_TOPIC_OCC_GRID)
client.subscribe(MQTT_TOPIC_PATH_COMPLETED)
client.subscribe(MQTT_TOPIC_ODOMETRY)
client.subscribe(MQTT_TOPIC_BOTTLE)
client.on_message = on_message

# -----------------------------------------------------------------------------
# A* Implementation
# -----------------------------------------------------------------------------
def in_bounds(grid, r, c):
    return (0 <= r < grid.shape[0]) and (0 <= c < grid.shape[1])

def is_free(grid, r, c):
    return in_bounds(grid, r, c) and grid[r, c] == 1

def heuristic(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def neighbors_8(grid, r, c):
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
        nr = r + dr
        nc = c + dc
        if in_bounds(grid, nr, nc) and grid[nr, nc] == 1:
            yield nr, nc

def a_star(grid, start_rc, goal_rc):
    if not is_free(grid, start_rc[0], start_rc[1]):
        return None
    if not is_free(grid, goal_rc[0], goal_rc[1]):
        return None

    frontier = []
    heappush(frontier, (0, start_rc))
    came_from = {start_rc: None}
    cost_so_far = {start_rc: 0}

    while frontier:
        _, current = heappop(frontier)
        if current == goal_rc:
            return reconstruct_path(came_from, start_rc, goal_rc)

        for nxt in neighbors_8(grid, current[0], current[1]):
            cost = cost_so_far[current] + (math.sqrt(2) if (nxt[0]-current[0]) and (nxt[1]-current[1]) else 1)
            if nxt not in cost_so_far or cost < cost_so_far[nxt]:
                cost_so_far[nxt] = cost
                priority = cost + heuristic(nxt, goal_rc)
                came_from[nxt] = current
                heappush(frontier, (priority, nxt))
    return None

def reconstruct_path(came_from, start, goal):
    path = []
    current = goal
    while current is not None:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path

# -----------------------------------------------------------------------------
# Conversions
# -----------------------------------------------------------------------------
def grid_to_world(r, c, params):
    x = params["min_x"] + (c + 0.5) * params["resolution"]
    y = params["min_y"] + (r + 0.5) * params["resolution"]
    return (x, y)

def world_to_grid(x, y, params):
    c = int((x - params["min_x"]) / params["resolution"])
    r = int((y - params["min_y"]) / params["resolution"])
    return (r, c)

def wrap_angle_180(a_deg):
    return (a_deg + 180) % 360 - 180

# -----------------------------------------------------------------------------
# Random Target
# -----------------------------------------------------------------------------
def get_bottle_target(grid, params, robot_r, robot_c, robot_x, robot_y, robot_th_deg):
    global bottle_detected, bottle_x_norm
    
    if not bottle_detected:
        return None
    
    # Convert normalized bottle position to angle
    bottle_angle = bottle_x_norm * 45  # Scale to ±45 degrees
    target_angle_deg = wrap_angle_180(robot_th_deg + bottle_angle)
    
    # Create multiple candidate paths at different distances and angles
    candidates = []
    
    # Try different angles around the bottle direction
    for angle_offset in [-15, 0, 15]:
        path_angle = wrap_angle_180(target_angle_deg + angle_offset)
        
        # Try different distances
        for distance in np.linspace(MIN_DISTANCE, MAX_DISTANCE, 5):
            theta_rad = math.radians(path_angle)
            tx = robot_x + distance * math.cos(theta_rad)
            ty = robot_y + distance * math.sin(theta_rad)

            tr, tc = world_to_grid(tx, ty, params)
            if is_free(grid, tr, tc):
                path = a_star(grid, (robot_r, robot_c), (tr, tc))
                if path is not None:
                    # Score this path based on length and angle deviation
                    path_length = len(path)
                    angle_deviation = abs(angle_offset)
                    score = path_length + angle_deviation * 0.5
                    
                    candidates.append((score, path))
    
    # Return the best path if any were found
    if candidates:
        candidates.sort(key=lambda x: x[0])  # Sort by score
        return candidates[0][1]  # Return path with lowest score
        
    return None

def check_path_safety(path_rc, grid):
    """Check if path has enough clearance from obstacles"""
    if not path_rc:
        return False
        
    for r, c in path_rc:
        # Check surrounding cells for obstacles
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if not is_free(grid, r + dr, c + dc):
                    return False
    return True

def simplify_path(path_rc, max_waypoints=4):
    if len(path_rc) <= max_waypoints:
        return path_rc
    # Always keep first, last, and 2 mid points
    start = path_rc[0]
    end   = path_rc[-1]
    idx1  = len(path_rc) // 3
    idx2  = (2 * len(path_rc)) // 3
    return [start, path_rc[idx1], path_rc[idx2], end]

# -----------------------------------------------------------------------------
# Main Loop
# -----------------------------------------------------------------------------
def main():
    global occupancy_grid, grid_params
    global need_new_path, current_path
    global robot_x, robot_y, robot_th_deg

    plan_rate = 0.2  # 5Hz
    retry_count = 0
    max_retries = 3

    while True:
        time.sleep(plan_rate)

        if occupancy_grid is None:
            continue

        # Convert robot pose to grid
        rr, cc = world_to_grid(robot_x, robot_y, grid_params)
        if not in_bounds(occupancy_grid, rr, cc):
            print("[node_pathplanning.py] Robot out of bounds in grid!")
            continue

        # Check if current path is safe
        if current_path is not None:
            if not check_path_safety(current_path, occupancy_grid):
                print("[node_pathplanning.py] Path no longer safe, replanning...")
                need_new_path = True
                current_path = None

        if need_new_path or current_path is None:
            print("[node_pathplanning.py] Planning path to bottle...")
            
            path_rc = get_bottle_target(
                occupancy_grid, grid_params,
                rr, cc,
                robot_x, robot_y, robot_th_deg
            )

            if path_rc is not None and check_path_safety(path_rc, occupancy_grid):
                path_rc = simplify_path(path_rc, 4)
                path_xy = [grid_to_world(r, c, grid_params) for r, c in path_rc]

                msg = {
                    "path_rc": path_rc,
                    "path_xy": path_xy
                }
                client.publish(MQTT_TOPIC_PATH_PLAN, json.dumps(msg))
                current_path = path_rc
                need_new_path = False
                retry_count = 0
                print(f"[node_pathplanning.py] Published safe path with {len(path_rc)} waypoints")
            else:
                retry_count += 1
                if retry_count >= max_retries:
                    print("[node_pathplanning.py] Failed to find safe path after multiple attempts")
                    retry_count = 0
                    time.sleep(1.0)  # Wait longer before trying again
                else:
                    print(f"[node_pathplanning.py] Retrying path planning (attempt {retry_count})")

try:
    main()
except KeyboardInterrupt:
    print("\n[node_pathplanning.py] Interrupted by user.")
finally:
    client.loop_stop()
    client.disconnect()
    print("[node_pathplanning.py] Shutdown.")
