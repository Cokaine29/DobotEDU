import sys
import os
import time

sys.path.append(r"d:\DobotEDU")

# Monkey-Patch DobotRPC to bypass port 10001 connection hang
try:
    import DobotRPC.RPCClient
    import asyncio

    class MockWS:
        @property
        def open(self):
            return True
        async def send(self, *args, **kwargs):
            pass
        async def recv(self, *args, **kwargs):
            await asyncio.sleep(36000)

    original_init = DobotRPC.RPCClient.RPCClient.__init__
    original_wait = DobotRPC.RPCClient.RPCClient.wait_for_connected
    original_is_connected = DobotRPC.RPCClient.RPCClient.is_connected

    def patched_init(self, ip="localhost", port=9090, *args, **kwargs):
        if port == 10001:
            self._RPCClient__ip = ip
            self._RPCClient__port = port
            self._RPCClient__ws = MockWS()
            self._RPCClient__exchange_map = {}
            self._RPCClient__recv_task_timer = None
            self._RPCClient__client_name = "MockClient-10001"
            self._RPCClient__loop = asyncio.get_event_loop()
            return
        return original_init(self, ip, port, *args, **kwargs)

    async def patched_wait_for_connected(self):
        if self._RPCClient__port == 10001:
            return
        return await original_wait(self)

    @property
    def patched_is_connected(self):
        if self._RPCClient__port == 10001:
            return True
        return original_is_connected.fget(self)

    DobotRPC.RPCClient.RPCClient.__init__ = patched_init
    DobotRPC.RPCClient.RPCClient.wait_for_connected = patched_wait_for_connected
    DobotRPC.RPCClient.RPCClient.is_connected = patched_is_connected
except Exception as e:
    pass

from DobotEDU import dobot_edu
from magician_go_lite.core.lite_helper import safe_connect, safe_disconnect

PORT = "COM6"

# Define the graph representing the city road grid
# Nodes are represented by (X, Y) coordinates in cm
GRAPH = {
    (0, 0): [(100, 0), (0, 50)],
    (100, 0): [(0, 0), (250, 0), (100, 50)],
    (250, 0): [(100, 0), (250, 50)],
    
    (0, 50): [(0, 0), (0, 100), (50, 50)],
    (50, 50): [(0, 50), (100, 50)], # Supermarket
    (100, 50): [(100, 0), (100, 100), (50, 50), (200, 50)],
    (200, 50): [(100, 50), (250, 50)], # Warehouse
    (250, 50): [(250, 0), (250, 100), (200, 50)],
    
    (0, 100): [(0, 50), (0, 150)], # Apartment
    (100, 100): [(100, 50), (100, 150), (150, 100)],
    (150, 100): [(100, 100)], # Small House
    (250, 100): [(250, 50), (250, 150)],
    
    (0, 150): [(0, 100), (100, 150)],
    (100, 150): [(100, 100), (0, 150), (250, 150)],
    (250, 150): [(250, 100), (100, 150)]
}

LANDMARKS = {
    "START": (0, 0),
    "APARTMENT": (0, 100),
    "SUPERMARKET": (50, 50),
    "HOUSE": (150, 100),
    "SMALL_HOUSE": (150, 100),
    "WAREHOUSE": (200, 50)
}

def bfs_path(start, goal):
    """Breadth-First Search to find the shortest path of coordinates."""
    if start == goal:
        return [start]
    queue = [[start]]
    visited = {start}
    while queue:
        path = queue.pop(0)
        node = path[-1]
        for neighbor in GRAPH.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                new_path = list(path)
                new_path.append(neighbor)
                if neighbor == goal:
                    return new_path
                queue.append(new_path)
    return None

def normalize_angle(angle):
    """Normalize angle to [-180, 180] degrees."""
    while angle > 180:
        angle -= 360
    while angle <= -180:
        angle += 360
    return angle

def get_target_heading(from_node, to_node):
    """Get target heading direction in degrees based on grid coordinates."""
    dx = to_node[0] - from_node[0]
    dy = to_node[1] - from_node[1]
    if dx > 10:   return 0    # East
    if dy > 10:   return 90   # North
    if dx < -10:  return 180  # West
    if dy < -10:  return -90  # South
    return 0

def main():
    dobot_edu.set_portname(PORT)
    lite = dobot_edu.m_lite
    go = dobot_edu.magiciango

    print(f"Connecting to Magician Lite on {PORT} to establish serial session...")
    try:
        safe_connect(lite)
    except Exception as e:
        print(f"[ERROR] Could not connect to Magician Lite: {e}")
        return

    print("Checking connection to Magician GO...")
    try:
        battery = go.get_power_voltage()
        print(f"[OK] Battery: {battery.get('powerPercentage', 'N/A')}% ({battery.get('powerVoltage', 'N/A')} V)")
    except Exception as e:
        print(f"[ERROR] Could not query Magician GO: {e}")
        safe_disconnect(lite)
        return

    # Reset Odometer at START box
    print("\nInitializing Odometer to (0,0) and Yaw 0°...")
    go.set_odometer_data(x=0, y=0, yaw=0)
    time.sleep(1.0)

    current_node = (0, 0)
    current_heading = 0 # 0=East, 90=North, 180=West, -90=South

    print("\n--- Magician GO City Navigation Terminal ---")
    print("Available Landmarks: START, APARTMENT, SUPERMARKET, HOUSE, WAREHOUSE")
    print("Type 'exit' or press Ctrl+C to quit.")
    print("-" * 60)

    try:
        while True:
            dest_input = input(f"\nCurrent Location: {current_node}. Enter destination: ").strip().upper()
            if not dest_input:
                continue
            if dest_input == "EXIT":
                break
            
            # Map input to node
            goal_node = None
            if dest_input in LANDMARKS:
                goal_node = LANDMARKS[dest_input]
            else:
                # Check if user typed coordinates directly, e.g. "100,50"
                try:
                    parts = dest_input.split(",")
                    x_t = int(parts[0].strip())
                    y_t = int(parts[1].strip())
                    goal_node = (x_t, y_t)
                    if goal_node not in GRAPH:
                        print(f"[ERROR] Coordinate {goal_node} is not a valid intersection on the map!")
                        continue
                except Exception:
                    print(f"[ERROR] Unknown landmark or coordinates format: '{dest_input}'")
                    continue
            
            if goal_node == current_node:
                print(f"[STATUS] Already at destination: {current_node}")
                continue
            
            path = bfs_path(current_node, goal_node)
            if not path:
                print(f"[ERROR] No valid road path found from {current_node} to {goal_node}!")
                continue
            
            print(f"[PATH] Planned Route: {' -> '.join(str(n) for n in path)}")
            time.sleep(1.0)
            
            # Execute path waypoint-by-waypoint
            for idx in range(len(path) - 1):
                from_node = path[idx]
                to_node = path[idx + 1]
                print(f"\n--- Leg {idx+1}/{len(path)-1}: {from_node} -> {to_node} ---")
                
                # 1. Determine target heading and turn robot
                target_heading = get_target_heading(from_node, to_node)
                turn_angle = normalize_angle(target_heading - current_heading)
                
                if abs(turn_angle) > 5:
                    print(f"[STEER] Rotating {turn_angle}° to face heading {target_heading}°...")
                    go.set_rotate(r=int(turn_angle), Vr=20)
                    time.sleep(abs(turn_angle) * 0.03 + 1.5) # Wait for rotation to finish
                
                current_heading = target_heading
                
                # 2. Drive to waypoint using line tracking + odometer limit
                print(f"[DRIVE] Tracing road to {to_node}...")
                go.set_trace_speed(speed=20)
                time.sleep(0.1)
                go.set_auto_trace(trace=2) # White line tracking mode
                
                # Monitor coordinate position
                reached = False
                tolerance = 5.0 # Stop 5cm before the target to account for deceleration
                keep_alive_timer = time.time()
                
                while not reached:
                    time.sleep(0.1)
                    
                    # Periodic keep-alive for the arm (every 1.2s)
                    if time.time() - keep_alive_timer > 1.2:
                        try:
                            lite.get_pose()
                        except Exception:
                            pass
                        keep_alive_timer = time.time()
                    
                    # Read odometer coordinates
                    try:
                        odo = go.get_odometer_data()
                        x_curr = odo.get('x', from_node[0])
                        y_curr = odo.get('y', from_node[1])
                    except Exception:
                        continue
                    
                    # Check reach condition depending on travel direction
                    if current_heading == 0:     # East (X increases)
                        reached = (x_curr >= to_node[0] - tolerance)
                    elif current_heading == 180:  # West (X decreases)
                        reached = (x_curr <= to_node[0] + tolerance)
                    elif current_heading == 90:   # North (Y increases)
                        reached = (y_curr >= to_node[1] - tolerance)
                    elif current_heading == -90:  # South (Y decreases)
                        reached = (y_curr <= to_node[1] + tolerance)
                
                # 3. Arrived at waypoint: Stop and align
                print(f"[ARRIVED] Reached waypoint: {to_node}")
                go.set_auto_trace(trace=0)
                time.sleep(0.1)
                go.set_trace_speed(speed=0)
                time.sleep(0.5)
                
                # Update current node position
                current_node = to_node
            
            # Destination reached chime
            print(f"\n[SUCCESS] Arrived at destination landmark: {dest_input} ({current_node})!")
            go.set_buzzer_sound(1, 1000, 1)
            time.sleep(0.3)
            go.set_buzzer_sound(1, 0, 0)
            
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        print("\nStopping robot safely...")
        try:
            go.set_trace_speed(speed=0)
            time.sleep(0.1)
            go.set_auto_trace(trace=0)
        except Exception:
            pass
        safe_disconnect(lite)

if __name__ == "__main__":
    main()
