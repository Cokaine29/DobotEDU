import sys
import os
import time

sys.path.append(r"d:\DobotEDU")
from DobotEDU import dobot_edu
from magician_go_lite.core.lite_helper import safe_connect, safe_disconnect

PORT = "COM6"

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Silent Patrol Test")
    parser.add_argument("--speed", type=int, default=12, help="Patrol speed (default: 12)")
    args = parser.parse_args()
    speed = args.speed

    dobot_edu.set_portname(PORT)
    lite = dobot_edu.m_lite
    go = dobot_edu.magiciango

    print(f"Connecting to Magician Lite on {PORT}...")
    try:
        safe_connect(lite)
    except Exception as e:
        print(f"[ERROR] Could not connect: {e}")
        return

    try:
        print(f"\n=== SILENT PATROL TEST ({speed} cm/s for 15 seconds) ===")
        print("This script will start patrol and then go COMPLETELY silent (no polling at all).")
        print("We want to see if the robot turns left perfectly without any over-steering.")
        
        go.set_trace_speed(speed=speed)
        time.sleep(0.1)
        go.set_auto_trace(trace=1)
        
        print("[STATUS] Patrol started. Going silent with 1.5s keep-alive slices for 15 seconds. Watch the turns...")
        # 10 slices of 1.5 seconds = 15 seconds total
        for i in range(10):
            time.sleep(1.5)
            try:
                lite.get_pose() # Keep DobotLink alive without flooding
            except Exception:
                pass

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
