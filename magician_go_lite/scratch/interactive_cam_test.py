import sys
import os
import time

sys.path.append(r"d:\DobotEDU")
from DobotEDU import dobot_edu
from magician_go_lite.core.lite_helper import get_lite, safe_connect, safe_disconnect

PORT = "COM6"

def main():
    print("Connecting to Magician Lite...")
    lite = get_lite(PORT)
    try:
        safe_connect(lite)
        
        go = dobot_edu.beta_go
        print("Activating Arm Camera color block detection model (index 1)...")
        go.set_arm_camera_model(1)
        time.sleep(2.0)
        
        print("\n=== Real-time Camera Polling ===")
        print("Move the red block around on the table/chassis under the camera.")
        print("Watch the output below to see when it is detected.")
        print("Press Ctrl+C to stop.\n")
        
        while True:
            try:
                objs = go.get_arm_camera_obj()
                count = objs.get('count', 0)
                if count > 0:
                    print(f"[{time.strftime('%H:%M:%S')}] Detected {count} objects: {objs.get('dl_obj')}")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] No objects detected.")
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        safe_disconnect(lite)

if __name__ == "__main__":
    main()
