import sys
import os
import time

sys.path.append(r"d:\DobotEDU")
from DobotEDU import dobot_edu
from magician_go_lite.core.lite_helper import safe_connect, safe_disconnect

PORT = "COM6"

def main():
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
        print("\nTesting set_rotate: The robot should rotate 90 degrees left.")
        print("Starting in 2 seconds...")
        time.sleep(2.0)
        
        # Test relative rotate 90 degrees left
        res = go.set_rotate(r=90, Vr=20)
        print(f"set_rotate result: {res}")
        time.sleep(3.0)

    except KeyboardInterrupt:
        pass
    finally:
        safe_disconnect(lite)

if __name__ == "__main__":
    main()
