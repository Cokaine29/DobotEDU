import sys
import os
import time

sys.path.append(r"d:\DobotEDU")
from DobotEDU import dobot_edu
from magician_go_lite.core.lite_helper import get_lite, safe_connect, safe_disconnect, read_stable_pose

PORT = "COM6"

def main():
    print("Connecting to Magician Lite...")
    lite = get_lite(PORT)
    try:
        safe_connect(lite)
        
        print("\n--- Physical Z Height Measurement ---")
        print("1. Press the unlock button on the arm.")
        print("2. Place the suction cup directly on top of a block on the chassis floor (as if it's picking it).")
        input("   Press [Enter] when ready to read coordinates...")
        
        pose = read_stable_pose(lite)
        if pose is not None:
            x, y, z, r = pose
            print(f"\n[MEASUREMENT] Current Pose: X={x:.2f} mm, Y={y:.2f} mm, Z={z:.2f} mm")
            print(f"Use this Z height as the pick-z parameter! (e.g. --pick-z {z:.1f})")
        else:
            print("[ERROR] Could not read arm pose.")
            
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        safe_disconnect(lite)

if __name__ == "__main__":
    main()
