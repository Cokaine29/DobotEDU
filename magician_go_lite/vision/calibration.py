"""
calibration.py
==============
Interactive 3-point calibration tool for the Magician Lite on Magician GO.

Usage:
  # Calibrate the chassis floor (block scanning)
  .venv\\Scripts\\python.exe magician_go_lite/vision/calibration.py --target chassis --port COM6
  
  # Calibrate the ground (box scanning)
  .venv\\Scripts\\python.exe magician_go_lite/vision/calibration.py --target ground --port COM6
"""

import sys
import os
import time
import json
import argparse
import cv2
import numpy as np

# Monkey-Patch DobotRPC to bypass port 10001 connection hang
try:
    import DobotRPC.RPCClient
    original_wait = DobotRPC.RPCClient.RPCClient.wait_for_connected
    original_is_connected = DobotRPC.RPCClient.RPCClient.is_connected

    async def patched_wait_for_connected(self):
        if self._RPCClient__port == 10001:
            return
        return await original_wait(self)

    @property
    def patched_is_connected(self):
        if self._RPCClient__port == 10001:
            return True
        return original_is_connected.fget(self)

    DobotRPC.RPCClient.RPCClient.wait_for_connected = patched_wait_for_connected
    DobotRPC.RPCClient.RPCClient.is_connected = patched_is_connected
except Exception as e:
    pass

# Append parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.lite_helper import get_lite, safe_connect, safe_disconnect, move_to, read_stable_pose
from DobotEDU import dobot_edu

def detect_calibration_block():
    """Polls the arm camera for any block, prioritizing red (id == 0), and returns its (x, y) coordinates."""
    go = dobot_edu.beta_go
    for attempt in range(10):
        try:
            objs = go.get_arm_camera_obj()
            if objs.get('count', 0) > 0:
                dl_objs = objs.get('dl_obj', [])
                # Try to find red block first
                for obj in dl_objs:
                    if obj.get('id') == 0:
                        return obj['x'], obj['y']
                # If no red, return first detected block
                if dl_objs:
                    return dl_objs[0]['x'], dl_objs[0]['y']
        except Exception as e:
            pass
        time.sleep(0.2)
    return None

def main():
    parser = argparse.ArgumentParser(description="Magician GO + Lite 3-Point Calibration")
    parser.add_argument("--target", type=str, default="chassis", choices=["chassis", "ground"],
                        help="Calibration target: 'chassis' (block pick area) or 'ground' (box drop area)")
    parser.add_argument("--port", type=str, default="COM6", help="COM port for Magician Lite")
    parser.add_argument("--scan-x", type=float, default=None, help="Custom Scan position X")
    parser.add_argument("--scan-y", type=float, default=None, help="Custom Scan position Y")
    parser.add_argument("--scan-z", type=float, default=None, help="Custom Scan position Z")
    parser.add_argument("--scan-r", type=float, default=None, help="Custom Scan position R")
    args = parser.parse_args()

    print(f"=== Magician GO + Lite Calibration [{args.target.upper()} Target] ===")
    print(f"Port: {args.port}")
    print("Ensure DobotLab is open and connected to 'Magician GO & Magician Lite' in the background.\n")

    # Set port name FIRST so that decorators on beta_go/lite methods receive the port parameter correctly
    dobot_edu.set_portname(args.port)

    # Determine scanning coordinates and config file path
    if args.target == "chassis":
        default_x, default_y, default_z, default_r = 0.0, -241.9, 66.8, -90.0
        config_name = "calibration_chassis.json"
    else:
        default_x, default_y, default_z, default_r = 241.0, 0.0, 149.3, 0.0
        config_name = "calibration_ground.json"

    SCAN_X = args.scan_x if args.scan_x is not None else default_x
    SCAN_Y = args.scan_y if args.scan_y is not None else default_y
    SCAN_Z = args.scan_z if args.scan_z is not None else default_z
    SCAN_R = args.scan_r if args.scan_r is not None else default_r

    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", config_name))
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    # Connect to Lite FIRST to establish the connection session
    lite = get_lite(args.port)
    try:
        safe_connect(lite)
        
        # Initialize arm camera model AFTER connection is established
        print("Activating Arm Camera color block detection model (index 1)...")
        go = dobot_edu.beta_go
        try:
            res = go.set_arm_camera_model(1)
            print(f"[OK] Arm camera model set result: {res}")
        except Exception as e:
            print(f"[ERROR] Failed to set arm camera model: {e}")
            return

        print("\nHoming robot...")
        lite.set_homecmd()
        print("[OK] Homing done.")
        
        # Set movement speeds (slow for calibration safety)
        lite.set_ptpcommon_params(velocity_ratio=40, acceleration_ratio=20)
        
        # Move to Scan Position
        print(f"\nMoving to scan position (hover first): X={SCAN_X}, Y={SCAN_Y}, Z=150.0...")
        lite.set_ptpcmd(ptp_mode=1, x=SCAN_X, y=SCAN_Y, z=150.0, r=SCAN_R)
        time.sleep(3.0)
        print(f"Descending to scan height Z={SCAN_Z}...")
        lite.set_ptpcmd(ptp_mode=1, x=SCAN_X, y=SCAN_Y, z=SCAN_Z, r=SCAN_R)
        time.sleep(2.0)

        pts_pixel = []
        pts_robot = []

        # Perform 3-point routine
        for i in range(1, 4):
            print(f"\n--- CALIBRATION POINT {i}/3 ---")
            print("1. Place the calibration block on the target surface in the camera view.")
            input("   Press [Enter] when the block is in position to capture...")
            
            center = detect_calibration_block()
            if center is None:
                print("   [ERROR] Block not detected in view. Check lighting/placement.")
                # Allow retry
                input("   Adjust block position, then press [Enter] to try again...")
                center = detect_calibration_block()
                if center is None:
                    print("   [ERROR] Still not detected. Skipping calibration.")
                    return
            
            u, v = center
            print(f"   [OK] Detected block at pixel: u={u}, v={v}")
            
            # User guides the arm
            print("2. Press the unlock button on the arm and physically align the suction cup/gripper")
            print("   directly on top of the block center.")
            print("3. Lightly press it down so it touches the block.")
            input("   Press [Enter] here once the arm is aligned...")
            
            pose = read_stable_pose(lite)
            if pose is None:
                print("   [ERROR] Could not read arm position. Retrying point...")
                return
                
            x_rob, y_rob = pose[0], pose[1]
            print(f"   [OK] Recorded Robot Pose: X={x_rob:.2f} mm, Y={y_rob:.2f} mm")
            
            pts_pixel.append([u, v])
            pts_robot.append([x_rob, y_rob])
            
            # Re-center arm
            print("\nRe-centering arm to Scan Position (hover first)...")
            lite.set_ptpcmd(ptp_mode=1, x=SCAN_X, y=SCAN_Y, z=150.0, r=SCAN_R)
            time.sleep(3.0)
            print("Descending to scan height...")
            lite.set_ptpcmd(ptp_mode=1, x=SCAN_X, y=SCAN_Y, z=SCAN_Z, r=SCAN_R)
            time.sleep(2.0)
            
        # Calculate transform matrix
        src = np.float32(pts_pixel)
        dst = np.float32(pts_robot)
        
        print("\nCalculating calibration matrix...")
        matrix = cv2.getAffineTransform(src, dst)
        
        # Save config
        calib_data = {
            "target": args.target,
            "scan_position": {
                "x": SCAN_X,
                "y": SCAN_Y,
                "z": SCAN_Z,
                "r": SCAN_R
            },
            "affine_matrix": matrix.tolist(),
            "points": {
                "pixel": pts_pixel,
                "robot": pts_robot
            }
        }
        
        with open(config_path, "w") as f:
            json.dump(calib_data, f, indent=4)
            
        print(f"\n[SUCCESS] Calibration complete! Saved matrix to: {config_path}")
        print("Affine Matrix:")
        print(matrix)
        
    except Exception as e:
        print(f"\n[ERROR] An exception occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        safe_disconnect(lite)

if __name__ == "__main__":
    main()
