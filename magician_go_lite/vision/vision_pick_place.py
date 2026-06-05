"""
vision_pick_place.py
====================
Main vision-guided sorting script for the Magician GO + Magician Lite combo.

Workflow:
  1. Move to Chassis Scan Position to locate the blocks stored on the chassis.
  2. Pick each block from the chassis and drop it in its corresponding taught colored square on the ground.

Usage:
  # Run in preview mode to verify object coordinates
  .venv\\Scripts\\python.exe magician_go_lite/vision/vision_pick_place.py --preview --port COM6
  
  # Run standard sorting with suction cup
  .venv\\Scripts\\python.exe magician_go_lite/vision/vision_pick_place.py --port COM6
  
  # Run with gripper
  .venv\\Scripts\\python.exe magician_go_lite/vision/vision_pick_place.py --port COM6 --gripper --pick-z 35.0 --drop-z 15.0
"""

import sys
import os
import time
import json
import argparse
import cv2
import numpy as np

# Append parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.lite_helper import get_lite, safe_connect, safe_disconnect, move_to, suction_on, suction_off, gripper_close, gripper_open
from DobotEDU import dobot_edu

# Scan position for Chassis floor slots
SCAN_CHASSIS = {"x": 0.0, "y": -241.9, "z": 66.8, "r": -90.0}

Z_HOVER = 80.0 # Hover height during travel

def load_calibration(filename):
    """Loads calibration matrix from magician_go_lite/config/."""
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", filename))
    if not os.path.exists(config_path):
        print(f"[ERROR] Calibration file '{config_path}' not found!")
        print("Please run: .venv\\Scripts\\python.exe magician_go_lite/vision/calibration.py --target chassis")
        sys.exit(1)
        
    with open(config_path, "r") as f:
        data = json.load(f)
    return np.array(data["affine_matrix"])

def load_drop_targets():
    """Loads drop targets from config/drop_targets.json."""
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "drop_targets.json"))
    if not os.path.exists(config_path):
        print(f"[ERROR] Drop targets file '{config_path}' not found!")
        print("Please run: .venv\\Scripts\\python.exe magician_go_lite/vision/teach_drop_targets.py")
        sys.exit(1)
        
    with open(config_path, "r") as f:
        data = json.load(f)
    return data

def detect_objects_via_api():
    """
    Polls dobot_edu.beta_go.get_arm_camera_obj() stably.
    Returns a list of dictionaries with structure:
    {
        "color": str,     # "red", "yellow", "blue", "green"
        "center": (x, y), # (u, v) pixel coordinates
        "w": int,
        "h": int,
        "id": int
    }
    """
    ID_TO_COLOR = {0: "red", 1: "yellow", 2: "blue", 3: "green"}
    go = dobot_edu.beta_go
    
    # Poll a few times to get a stable reading
    for attempt in range(5):
        try:
            objs = go.get_arm_camera_obj()
            count = objs.get('count', 0)
            if count > 0:
                dl_objs = objs.get('dl_obj', [])
                detected = []
                for obj in dl_objs:
                    color_id = obj.get('id')
                    if color_id in ID_TO_COLOR:
                        detected.append({
                            "color": ID_TO_COLOR[color_id],
                            "center": (obj['x'], obj['y']),
                            "w": obj.get('w', 0),
                            "h": obj.get('h', 0),
                            "id": color_id
                        })
                if detected:
                    return detected
        except Exception as e:
            print(f"  [WARN] Error polling camera: {e}")
        time.sleep(0.2)
    return []

def check_safety_bounds(x, y):
    """Safety boundary check for Magician Lite workspace on Magician GO chassis."""
    radius = np.sqrt(x**2 + y**2)
    return (150.0 <= radius <= 340.0)

def run_preview(args):
    """Preview mode to test camera API detection and coordinate mapping."""
    print("Starting vision preview mode...")
    print("This mode continuously polls the arm camera API and displays detected objects.")
    print("Press Ctrl+C to stop.")
    
    # Try loading calibrations and drop targets
    mat_chassis = None
    drop_targets = {}
    try:
        mat_chassis = load_calibration("calibration_chassis.json")
        print("[INFO] Chassis calibration loaded.")
    except SystemExit:
        print("[WARN] calibration_chassis.json not found.")
    try:
        drop_targets = load_drop_targets()
        print("[INFO] Drop targets loaded.")
    except SystemExit:
        print("[WARN] drop_targets.json not found.")
        
    lite = get_lite(args.port)
    try:
        safe_connect(lite)
        
        go = dobot_edu.beta_go
        try:
            go.set_arm_camera_model(1)
            time.sleep(1.0)
        except Exception as e:
            print(f"[ERROR] Failed to set arm camera model: {e}")
            return

        while True:
            objs = go.get_arm_camera_obj()
            count = objs.get('count', 0)
            print(f"\n[{time.strftime('%H:%M:%S')}] Detected {count} objects:")
            if count > 0:
                dl_objs = objs.get('dl_obj', [])
                ID_TO_COLOR = {0: "red", 1: "yellow", 2: "blue", 3: "green"}
                for obj in dl_objs:
                    color_id = obj.get('id')
                    color = ID_TO_COLOR.get(color_id, f"unknown({color_id})")
                    u, v = obj['x'], obj['y']
                    info = f"  - Color: {color.upper()} (id={color_id}), pixel: ({u}, {v}), size: {obj.get('w')}x{obj.get('h')}"
                    
                    # If we have chassis calibration, show mapped robot coordinates
                    if mat_chassis is not None:
                        pts = np.float32([[[u, v]]])
                        trans = cv2.transform(pts, mat_chassis)
                        rx, ry = trans[0][0]
                        info += f" | Chassis: X={rx:.1f}, Y={ry:.1f}"
                    
                    # Show matching drop target coordinate if taught
                    if color in drop_targets:
                        target = drop_targets[color]
                        info += f" | Drop Target: X={target['x']:.1f}, Y={target['y']:.1f}, Z={target['z']:.1f}"
                    print(info)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nPreview stopped.")
    finally:
        safe_disconnect(lite)

def main():
    parser = argparse.ArgumentParser(description="Magician GO + Lite Combo Pick & Place")
    parser.add_argument("--preview", action="store_true", help="Run vision-only preview mode")
    parser.add_argument("--port", type=str, default="COM6", help="COM port for Magician Lite")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (ignored, uses Dobot API)")
    parser.add_argument("--gripper", action="store_true", help="Use gripper instead of suction cup")
    parser.add_argument("--pick-z", type=float, default=None, help="Custom block pick height on chassis floor")
    parser.add_argument("--drop-z", type=float, default=None, help="Custom block drop height above ground boxes")
    parser.add_argument("--scan-x", type=float, default=0.0, help="Custom Chassis Scan position X")
    parser.add_argument("--scan-y", type=float, default=-241.9, help="Custom Chassis Scan position Y")
    parser.add_argument("--scan-z", type=float, default=66.8, help="Custom Chassis Scan position Z")
    parser.add_argument("--scan-r", type=float, default=-90.0, help="Custom Chassis Scan position R")
    args = parser.parse_args()
    
    scan_pos = {
        "x": args.scan_x,
        "y": args.scan_y,
        "z": args.scan_z,
        "r": args.scan_r
    }
    
    # Set port name FIRST so that decorators on beta_go/lite methods receive the port parameter correctly
    dobot_edu.set_portname(args.port)

    if args.preview:
        run_preview(args)
        return
        
    # Load calibrations
    print("Loading calibration and drop target files...")
    mat_chassis = load_calibration("calibration_chassis.json")
    drop_targets = load_drop_targets()
    print("[OK] Calibrations and drop targets loaded.")
    
    # Establish pick Z coordinate
    if args.pick_z is not None:
        pick_z = args.pick_z
    else:
        pick_z = 35.0 # default pick height from chassis floor
        
    print(f"End-effector: {'GRIPPER' if args.gripper else 'SUCTION CUP'}")
    print(f"Pick Z (Chassis): {pick_z:.1f} mm")
    if args.drop_z is not None:
        print(f"Custom Drop Z: {args.drop_z:.1f} mm")
    else:
        print("Using physically taught Z heights for dropping.")
    
    lite = get_lite(args.port)
    try:
        safe_connect(lite)
        
        # Initialize arm camera model via API AFTER connecting
        print("Activating Arm Camera color block detection model (index 1)...")
        go = dobot_edu.beta_go
        try:
            go.set_arm_camera_model(1)
            time.sleep(1.0)
        except Exception as e:
            print(f"[ERROR] Failed to set arm camera model: {e}")
            return
        
        print("\nHoming robot...")
        lite.set_homecmd()
        print("[OK] Homing complete.")
        
        lite.set_ptpcommon_params(velocity_ratio=80, acceleration_ratio=40)
        
        # ── STEP 1: Scan Chassis Blocks ───────────────────────────────────────
        print(f"\nMoving to Chassis Scan Position (hover first): X={scan_pos['x']}, Y={scan_pos['y']}, Z=150.0...")
        move_to(lite, scan_pos['x'], scan_pos['y'], 150.0, scan_pos['r'])
        print(f"Descending to scan height Z={scan_pos['z']}...")
        move_to(lite, scan_pos['x'], scan_pos['y'], scan_pos['z'], scan_pos['r'])
        time.sleep(1.0)
        
        print("\n--- STEP 1: Scan Chassis Blocks ---")
        print("Ensure the blocks to be sorted are placed on the chassis floor slots.")
        input("Press [Enter] when blocks are in position to scan...")
        
        blocks = detect_objects_via_api()
        if not blocks:
            print("[INFO] No blocks detected on the chassis floor. Exiting...")
            return
            
        print(f"[OK] Detected {len(blocks)} blocks on chassis: " + ", ".join([b["color"].upper() for b in blocks]))
        
        # ── STEP 2: Pick and Place Sequence ───────────────────────────────────
        for idx, block in enumerate(blocks):
            color = block["color"]
            u, v = block["center"]
            print(f"\n--- Processing Block {idx+1}/{len(blocks)} [{color.upper()}] ---")
            
            # Map block pixel to robot coordinates using chassis calibration
            pts = np.float32([[[u, v]]])
            trans = cv2.transform(pts, mat_chassis)
            block_x, block_y = trans[0][0]
            block_x = float(block_x)
            block_y = float(block_y)
            block_angle = scan_pos["r"]
            
            print(f"Block Chassis Pose: X={block_x:.1f}, Y={block_y:.1f}")
            
            # Verify block coordinates are safe
            if not check_safety_bounds(block_x, block_y):
                print(f"[SAFETY WARNING] Block coordinates ({block_x:.1f}, {block_y:.1f}) out of safe reach! Skipping.")
                continue
                
            # Verify drop target exists in taught targets
            if color not in drop_targets:
                print(f"[WARN] No drop target taught for color '{color.upper()}'. Skipping block.")
                continue
                
            target_box = drop_targets[color]
            drop_x = target_box["x"]
            drop_y = target_box["y"]
            drop_z_final = args.drop_z if args.drop_z is not None else target_box["z"]
            drop_angle = target_box["r"]
            
            print(f"Target Drop Pose: X={drop_x:.1f}, Y={drop_y:.1f}, Z={drop_z_final:.1f}")
            
            if not check_safety_bounds(drop_x, drop_y):
                print(f"[SAFETY WARNING] Target coordinates ({drop_x:.1f}, {drop_y:.1f}) out of safe reach! Skipping.")
                continue
                
            # A. Pick Sequence (from chassis)
            print(f"  Hovering over block...")
            move_to(lite, block_x, block_y, Z_HOVER, block_angle)
            
            print(f"  Descending to pick height Z={pick_z:.1f}...")
            move_to(lite, block_x, block_y, pick_z, block_angle)
            
            if args.gripper:
                print("  Closing gripper...")
                gripper_close(lite)
            else:
                print("  Suction cup ON...")
                suction_on(lite)
                
            print("  Lifting block...")
            move_to(lite, block_x, block_y, Z_HOVER, block_angle)
            
            # B. Place Sequence (to ground square)
            print(f"  Hovering over target {color.upper()} square...")
            move_to(lite, drop_x, drop_y, Z_HOVER, drop_angle)
            
            print(f"  Descending to drop height Z={drop_z_final:.1f}...")
            move_to(lite, drop_x, drop_y, drop_z_final, drop_angle)
            
            if args.gripper:
                print("  Opening gripper...")
                gripper_open(lite)
            else:
                print("  Suction cup OFF...")
                suction_off(lite)
                
            print("  Lifting away...")
            move_to(lite, drop_x, drop_y, Z_HOVER, drop_angle)
            
            print(f"[OK] Placed {color.upper()} block successfully.")
            
        # Finish
        print("\nAll blocks processed. Returning home...")
        lite.set_homecmd()
        print("[SUCCESS] Sorting run complete.")
        
    except Exception as e:
        print(f"\n[ERROR] Sorting execution failed: {e}")
        import traceback
        traceback.print_exc()
        try:
            if args.gripper: gripper_open(lite)
            else: suction_off(lite)
        except Exception: pass
    finally:
        safe_disconnect(lite)

if __name__ == "__main__":
    main()
