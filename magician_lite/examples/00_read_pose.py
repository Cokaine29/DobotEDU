"""
00_read_pose.py
===============
Reads the current pose of the robot cleanly.
Run this anytime to check where the arm is.

Also prints suggested safe coordinate ranges for your workspace.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import time
from pydobot import Dobot

PORT = "COM8"

try:
    device = Dobot(port=PORT, verbose=False)

    # Read pose multiple times until we get stable clean values
    stable_pose = None
    for attempt in range(5):
        time.sleep(0.3)
        device.ser.reset_input_buffer()
        time.sleep(0.1)
        pose = device.pose()
        x, y, z = pose[0], pose[1], pose[2]

        # Sanity check — Magician Lite workspace is roughly 0-400mm
        if abs(x) < 1000 and abs(y) < 1000 and abs(z) < 1000:
            stable_pose = pose
            break
        else:
            print(f"  [attempt {attempt+1}] Stale data, retrying ...")

    if stable_pose:
        x, y, z, r = stable_pose[0], stable_pose[1], stable_pose[2], stable_pose[3]
        j1, j2, j3, j4 = stable_pose[4], stable_pose[5], stable_pose[6], stable_pose[7]

        print(f"\n  Current Pose (Cartesian):")
        print(f"    X  = {x:.2f} mm")
        print(f"    Y  = {y:.2f} mm")
        print(f"    Z  = {z:.2f} mm")
        print(f"    R  = {r:.2f} deg")
        print(f"\n  Joint Angles:")
        print(f"    J1 = {j1:.2f} deg  (base rotation)")
        print(f"    J2 = {j2:.2f} deg  (lower arm)")
        print(f"    J3 = {j3:.2f} deg  (upper arm)")
        print(f"    J4 = {j4:.2f} deg  (end-effector)")

        # Suggest safe ranges based on current position
        safe_x_min = max(150, x - 60)
        safe_x_max = min(320, x + 60)
        safe_y_min = max(-100, y - 50)
        safe_y_max = min(100,  y + 50)
        safe_z_min = max(50,   z - 60)
        safe_z_max = min(200,  z + 50)

        print(f"\n  Suggested SAFE ranges from current position:")
        print(f"    X: {safe_x_min:.0f} to {safe_x_max:.0f} mm")
        print(f"    Y: {safe_y_min:.0f} to {safe_y_max:.0f} mm")
        print(f"    Z: {safe_z_min:.0f} to {safe_z_max:.0f} mm")
    else:
        print("\n[WARN] Could not get clean pose. Try re-running the script.")

except Exception as e:
    import traceback
    traceback.print_exc()

finally:
    try:
        device.close()
    except Exception:
        pass
