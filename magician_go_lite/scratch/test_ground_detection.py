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
    safe_connect(lite)
    
    print("Homing robot...")
    lite.set_homecmd()
    time.sleep(2.0)
    
    go = dobot_edu.beta_go
    print("Activating Arm Camera color block detection model (index 1)...")
    go.set_arm_camera_model(1)
    time.sleep(2.0)
    
    # Move to ground scan position
    print("Moving to Ground Scan Position (X=241.0, Y=0.0, Z=149.3, R=0.0)...")
    move_to(lite, 241.0, 0.0, 149.3, 0.0)
    time.sleep(2.0)
    
    print("Polling detected objects...")
    for i in range(1, 11):
        try:
            objs = go.get_arm_camera_obj()
            print(f"[{i}] Count: {objs.get('count', 0)}")
            if objs.get('count', 0) > 0:
                print(f"    Objects: {objs.get('dl_obj')}")
        except Exception as e:
            print(f"[{i}] Read error: {e}")
        time.sleep(1.0)
        
    print("Returning home...")
    lite.set_homecmd()
    safe_disconnect(lite)

if __name__ == "__main__":
    main()
