import sys
import os
import time

sys.path.append(r"d:\DobotEDU")
from DobotEDU import dobot_edu
from magician_go_lite.core.lite_helper import get_lite, safe_connect, safe_disconnect, move_to

PORT = "COM6"

def main():
    print("Connecting to Magician Lite...")
    lite = get_lite(PORT)
    try:
        safe_connect(lite)
        
        # Move to Chassis Scan Position
        print("Moving to Chassis Scan Position (X=0.0, Y=-241.9, Z=66.8, R=-90.0)...")
        move_to(lite, 0.0, -241.9, 66.8, -90.0)
        time.sleep(1.0)
        
        go = dobot_edu.beta_go
        print("Activating Arm Camera color block detection model (index 1)...")
        go.set_arm_camera_model(1)
        time.sleep(2.0)
        
        print("\n=== Real-time Chassis Polling ===")
        print("Move the red block around in the chassis floor slots.")
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
        # Return to home
        print("Returning home...")
        lite.set_homecmd()
        safe_disconnect(lite)

if __name__ == "__main__":
    main()
