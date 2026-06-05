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
        
        go = dobot_edu.beta_go
        print("Activating Arm Camera color block detection model (index 1)...")
        go.set_arm_camera_model(1)
        time.sleep(2.0)
        
        print("\n=== Starting Z-Height Sweep ===")
        print("Make sure the RED block is placed on the table directly under the arm's end-effector.")
        
        for z in range(140, 40, -10):
            print(f"\nMoving to X=241.0, Y=0.0, Z={z}.0...")
            move_to(lite, 241.0, 0.0, float(z), 0.0)
            time.sleep(1.5)
            
            print(f"Polling at Z={z}.0:")
            detected_any = False
            for attempt in range(5):
                try:
                    objs = go.get_arm_camera_obj()
                    count = objs.get('count', 0)
                    if count > 0:
                        print(f"  Attempt {attempt+1}: Detected {count} objects: {objs.get('dl_obj')}")
                        detected_any = True
                    else:
                        print(f"  Attempt {attempt+1}: No objects")
                except Exception as e:
                    print(f"  Attempt {attempt+1}: Error: {e}")
                time.sleep(0.4)
                
            if detected_any:
                print(f"[FOUND] Detections occurred at Z={z}.0!")
                
        print("\nSweep complete.")
        
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        print("Returning home...")
        lite.set_homecmd()
        safe_disconnect(lite)

if __name__ == "__main__":
    main()
