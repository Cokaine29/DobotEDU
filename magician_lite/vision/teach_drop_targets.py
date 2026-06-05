"""
teach_drop_targets.py
=====================
Interactive teaching tool to define drop locations for each color.

Workflow:
  For each color (Red, Yellow, Blue, Green):
    1. User unlocks the arm and moves the suction cup to the desired bin location.
    2. User presses Enter in the terminal.
    3. Script reads the physical (X, Y, Z, R) coordinates and saves them.
  Saves the taught coordinates to 'drop_targets.json'.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import os
import json
import time
from pydobot import Dobot

PORT = "COM8"

def read_stable_pose(device, retries=5):
    """Robustly reads current robot pose by clearing stale serial buffer data."""
    for attempt in range(retries):
        time.sleep(0.2)
        device.ser.reset_input_buffer()
        time.sleep(0.1)
        pose = device.pose()
        x, y, z = pose[0], pose[1], pose[2]
        
        # Check for sane values (Magician Lite bounds)
        if abs(x) < 1000 and abs(y) < 1000 and abs(z) < 1000:
            return pose
    return None

def main():
    print("=== Teach Drop targets for Dobot Magician Lite ===")
    print("Make sure DobotLab is closed to free up the COM port.\n")
    
    print(f"Connecting to Magician Lite on {PORT} ...")
    try:
        device = Dobot(port=PORT, verbose=False)
        print("[OK] Connected!\n")
        
        drop_targets = {}
        colors = ["red", "yellow", "blue", "green"]
        
        for color in colors:
            print(f"--- TEACH {color.upper()} DROP TARGET ---")
            print(f"1. Press the unlock button on the arm and physically move the suction cup")
            print(f"   to the exact location/bin where you want to drop {color.upper()} blocks.")
            print(f"2. Lower it to the table surface (or just above the bottom of the bin).")
            input("   Press [Enter] here once the arm is positioned...")
            
            # Read pose
            pose = read_stable_pose(device)
            if pose is None:
                print("   [ERROR] Could not read arm position. Let's try this color again.")
                # retry color by prepending/looping
                # Simple way is to just let them retry this step
                input("   Failed to read pose. Check serial connection, then press [Enter] to try again...")
                pose = read_stable_pose(device)
                if pose is None:
                    print("   [ERROR] Still could not read. Skipping this color.")
                    continue
            
            x, y, z, r = pose[0], pose[1], pose[2], pose[3]
            print(f"   [OK] Recorded target for {color.upper()}: X={x:.1f}, Y={y:.1f}, Z={z:.1f}, R={r:.1f}\n")
            
            drop_targets[color] = {
                "x": round(x, 1),
                "y": round(y, 1),
                "z": round(z, 1),
                "r": round(r, 1)
            }
            
        # Save to drop_targets.json
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "drop_targets.json"))
        with open(config_path, "w") as f:
            json.dump(drop_targets, f, indent=4)
            
        print(f"[SUCCESS] Teaching complete! Saved targets to: {config_path}")
        print(json.dumps(drop_targets, indent=2))
        
    except Exception as e:
        print(f"\n[ERROR] An exception occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            device.close()
            print("Disconnected from Dobot.")
        except Exception:
            pass

if __name__ == "__main__":
    main()
