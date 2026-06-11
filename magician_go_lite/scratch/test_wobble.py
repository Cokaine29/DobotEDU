import sys
import os
import time

sys.path.append(r"d:\DobotEDU")
from DobotEDU import dobot_edu
from magician_go_lite.core.lite_helper import safe_connect, safe_disconnect, keep_alive_sleep

PORT = "COM6"

def main():
    dobot_edu.set_portname(PORT)
    lite = dobot_edu.m_lite
    go = dobot_edu.magiciango
    beta_go = dobot_edu.beta_go

    print(f"Connecting to Magician Lite on {PORT}...")
    try:
        safe_connect(lite)
    except Exception as e:
        print(f"[ERROR] Could not connect: {e}")
        return

    try:
        print("\n=== PHASE 1: Running trace WITHOUT camera polling (20 seconds) ===")
        print("Check if the robot drives smoothly...")
        go.set_trace_speed(speed=20)
        time.sleep(0.1)
        go.set_auto_trace(trace=1)
        
        # Sleep for 20 seconds using keep-alive to keep the connection open
        keep_alive_sleep(lite, 20.0)

        print("\n=== PHASE 2: Running trace WITH rapid camera polling (20 seconds) ===")
        print("Check if the robot starts wobbling...")
        start_time = time.time()
        while time.time() - start_time < 20.0:
            # Poll camera at 100ms interval
            beta_go.get_car_camera_obj()
            time.sleep(0.1)

        print("\n=== PHASE 3: Running trace WITHOUT camera polling again (20 seconds) ===")
        print("Check if it becomes smooth again...")
        keep_alive_sleep(lite, 20.0)

    except KeyboardInterrupt:
        pass
    finally:
        print("\nStopping robot...")
        try:
            go.set_trace_speed(speed=0)
            time.sleep(0.1)
            go.set_auto_trace(trace=0)
        except Exception:
            pass
        safe_disconnect(lite)

if __name__ == "__main__":
    main()
