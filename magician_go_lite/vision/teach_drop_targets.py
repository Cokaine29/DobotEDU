"""
teach_drop_targets.py
=====================
Interactive script to teach and record the physical coordinates of the
colored squares on the ground map.

Usage:
  .venv\\Scripts\\python.exe magician_go_lite/vision/teach_drop_targets.py --port COM6
"""

import sys
import os
import time
import json
import argparse

# Append parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.lite_helper import get_lite, safe_connect, safe_disconnect, read_stable_pose
from DobotEDU import dobot_edu

def main():
    parser = argparse.ArgumentParser(description="Teach Ground Drop Coordinates")
    parser.add_argument("--port", type=str, default="COM6", help="COM port for Magician Lite")
    args = parser.parse_args()

    print("=== Teach Ground Drop Targets ===")
    print(f"Port: {args.port}")
    print("Ensure DobotLab is open and connected to 'Magician GO & Magician Lite' in the background.\n")

    dobot_edu.set_portname(args.port)
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "drop_targets.json"))
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    lite = get_lite(args.port)
    try:
        safe_connect(lite)
        
        print("\nHoming robot...")
        lite.set_homecmd()
        print("[OK] Homing complete.")
        
        targets = {}
        colors = ["red", "yellow", "blue", "green"]
        
        for color in colors:
            print(f"\n--- TEACHING {color.upper()} TARGET ---")
            print(f"1. Press the unlock button on the arm and physically place the suction cup / gripper")
            print(f"   directly in the center of the {color.upper()} square on the ground map.")
            print(f"2. Make sure the end-effector is touching or is very close to the map surface.")
            input("   Press [Enter] once the arm is aligned...")
            
            pose = read_stable_pose(lite)
            if pose is None:
                print("   [ERROR] Could not read arm position. Retrying target...")
                # Repeat this color
                colors.insert(colors.index(color), color)
                continue
                
            x, y, z, r = pose
            targets[color] = {"x": x, "y": y, "z": z, "r": r}
            print(f"   [OK] Recorded {color.upper()}: X={x:.2f} mm, Y={y:.2f} mm, Z={z:.2f} mm, R={r:.2f} deg")
            
        # Save to config
        with open(config_path, "w") as f:
            json.dump(targets, f, indent=4)
            
        print(f"\n[SUCCESS] Saved drop targets to: {config_path}")
        
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")
    finally:
        safe_disconnect(lite)

if __name__ == "__main__":
    main()
