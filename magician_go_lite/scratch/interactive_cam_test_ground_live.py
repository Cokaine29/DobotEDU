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
        
        # Move to Ground Scan Z=90
        print("Moving to Ground Scan Position (X=241.0, Y=0.0, Z=90.0)...")
        move_to(lite, 241.0, 0.0, 90.0, 0.0)
        time.sleep(1.0)
        
        go = dobot_edu.beta_go
        print("Activating Arm Camera color block detection model (index 1)...")
        go.set_arm_camera_model(1)
        time.sleep(2.0)
        
        print("\n=== Live Ground Polling at Z=90.0 ===")
        print("Slowly slide the red block on the table under/around the arm.")
        print("Press Ctrl+C to stop.\n")
        
        while True:
            try:
                objs = go.get_arm_camera_obj()
                count = objs.get('count', 0)
                if count > 0:
                    print(f"[{time.strftime('%H:%M:%S')}] Detected {count} objects: {objs.get('dl_obj')}")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] No objects.")
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        print("Returning home...")
        lite.set_homecmd()
        safe_disconnect(lite)

if __name__ == "__main__":
    main()
