import sys
import os
import time

sys.path.append(r"d:\DobotEDU")
from DobotEDU import dobot_edu
from magician_go_lite.core.lite_helper import safe_connect, safe_disconnect

PORT = "COM6"

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Silent Patrol Test with Trace Mode")
    parser.add_argument("--speed", type=int, default=12, help="Patrol speed (default: 12)")
    parser.add_argument("--trace", type=int, default=2, help="Trace mode: 1 = Black line, 2 = White line")
    args = parser.parse_args()
    speed = args.speed
    trace_mode = args.trace

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
        print(f"\n=== TRACE MODE TEST (Speed={speed} cm/s, TraceMode={trace_mode} for 15 seconds) ===")
        print("Testing if trace=2 configures the robot to track the white line in the center correctly.")
        
        go.set_trace_speed(speed=speed)
        time.sleep(0.1)
        
        # Start trace using the custom trace mode parameter
        go.set_auto_trace(trace=trace_mode)
        
        print("[STATUS] Patrol started. Going silent with 1.5s keep-alive slices. Watch the turns...")
        for i in range(10):
            time.sleep(1.5)
            try:
                lite.get_pose()
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
