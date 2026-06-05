"""
calibration.py
==============
Interactive 3-point calibration tool for the Magician Lite on Magician GO.

Usage:
  # Calibrate the chassis floor (block scanning)
  python magician_go_lite/vision/calibration.py --target chassis --port COM6 --camera 0
  
  # Calibrate the ground (box scanning)
  python magician_go_lite/vision/calibration.py --target ground --port COM6 --camera 0
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
from core.lite_helper import get_lite, safe_connect, safe_disconnect, move_to, read_stable_pose

def detect_red_block(img):
    """Detects a red block in the frame and returns its centroid (u, v) or None."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Red HSV bounds (covers two ranges due to wrap-around at 180)
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)
    
    # Clean up noise
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    best_cnt = None
    max_area = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 300: # ignore tiny noise
            if area > max_area:
                max_area = area
                best_cnt = cnt
                
    if best_cnt is not None:
        M = cv2.moments(best_cnt)
        if M['m00'] != 0:
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            return cx, cy
            
    return None

def main():
    parser = argparse.ArgumentParser(description="Magician GO + Lite 3-Point Calibration")
    parser.add_argument("--target", type=str, default="chassis", choices=["chassis", "ground"],
                        help="Calibration target: 'chassis' (block pick area) or 'ground' (box drop area)")
    parser.add_argument("--port", type=str, default="COM6", help="COM port for Magician Lite")
    parser.add_argument("--camera", type=int, default=0, help="USB camera index (default: 0)")
    args = parser.parse_args()

    print(f"=== Magician GO + Lite Calibration [{args.target.upper()} Target] ===")
    print(f"Port: {args.port} | Camera Index: {args.camera}")
    print("Close DobotLab to free the COM port.\n")

    # Determine scanning coordinates and config file path
    if args.target == "chassis":
        SCAN_X, SCAN_Y, SCAN_Z, SCAN_R = 0.0, -241.9, 66.8, -90.0
        config_name = "calibration_chassis.json"
    else:
        SCAN_X, SCAN_Y, SCAN_Z, SCAN_R = 241.0, 0.0, 149.3, 0.0
        config_name = "calibration_ground.json"

    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", config_name))
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    # Initialize camera test
    print(f"Testing camera index {args.camera}...")
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"[ERROR] Could not open camera index {args.camera}. Check USB connection.")
        return
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("[ERROR] Could not read frame from camera.")
        return
    print("[OK] Camera is ready.\n")

    # Connect to Lite
    lite = get_lite(args.port)
    try:
        safe_connect(lite)
        
        print("\nHoming robot...")
        lite.set_homecmd()
        print("[OK] Homing done.")
        
        # Set movement speeds (slow for calibration safety)
        lite.set_ptpcommon_params(velocity_ratio=40, acceleration_ratio=20)
        
        # Move to Scan Position
        print(f"\nMoving to scan position: X={SCAN_X}, Y={SCAN_Y}, Z={SCAN_Z}, R={SCAN_R}...")
        lite.set_ptpcmd(ptp_mode=1, x=SCAN_X, y=SCAN_Y, z=SCAN_Z, r=SCAN_R)
        time.sleep(3.0)

        pts_pixel = []
        pts_robot = []

        # Perform 3-point routine
        for i in range(1, 4):
            print(f"\n--- CALIBRATION POINT {i}/3 ---")
            print("1. Place the RED block on the target surface in the camera view.")
            input("   Press [Enter] when the block is in position to capture...")
            
            # Capture frame
            cap = cv2.VideoCapture(args.camera)
            time.sleep(0.5) # allow auto-exposure
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                print("   [ERROR] Failed to capture frame. Retrying point...")
                i -= 1
                continue
                
            center = detect_red_block(frame)
            if center is None:
                print("   [ERROR] RED block not detected in view. Check lighting/placement.")
                cv2.imwrite("failed_calibration_detect.jpg", frame)
                print("   Snapshot saved to 'failed_calibration_detect.jpg' for analysis.")
                # Allow retry of the same index
                input("   Adjust block position, then press [Enter] to try again...")
                # We decrement i so it repeats this step
                # A simple decrement requires us to restart this point iteration
                # We can just decrement and run a loop logic
                # For safety, let's just let it repeat the capture
                cap = cv2.VideoCapture(args.camera)
                time.sleep(0.5)
                ret, frame = cap.read()
                cap.release()
                if ret:
                    center = detect_red_block(frame)
                
                if center is None:
                    print("   [ERROR] Still not detected. Skipping point (calibration will fail).")
                    return
            
            u, v = center
            print(f"   [OK] Detected RED block at pixel: u={u}, v={v}")
            
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
            print("\nRe-centering arm to Scan Position...")
            lite.set_ptpcmd(ptp_mode=1, x=SCAN_X, y=SCAN_Y, z=SCAN_Z, r=SCAN_R)
            time.sleep(3.0)
            
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
