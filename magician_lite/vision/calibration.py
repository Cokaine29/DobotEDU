"""
calibration.py
==============
Interactive 3-point calibration tool for the Dobot Magician Lite.

Workflow:
  1. Arm moves to a high Scan Position (X=220, Y=0, Z=130).
  2. For 3 different points, the user:
     - Places a RED block on the mat.
     - Script detects its pixel center (u, v) using camera index 0.
     - User unlocks the arm, moves the suction cup directly onto the block, and presses Enter.
     - Script records physical (X, Y).
  3. Computes the affine transformation matrix and saves it to 'calibration.json'.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import os
import json
import time
import cv2
import numpy as np
from pydobot import Dobot
from core.lite_move import setup_speed, move_to, send_home

PORT = "COM8"
CAMERA_INDEX = 0

# Fixed high-clearance Scan Position where the camera sees the whole workspace
# Set to match the official Home coordinates (X=241.02, Y=0.00, Z=149.33, R=0.00)
SCAN_X, SCAN_Y, SCAN_Z, SCAN_R = 241.0, 0.0, 149.3, 0.0

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
    print("=== Dobot Magician Lite Interactive Calibration ===")
    print("Make sure DobotLab is closed to free up the COM port.\n")
    
    # Initialize camera to make sure it works before starting robot movement
    print(f"Testing camera index {CAMERA_INDEX} ...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("[ERROR] Could not open camera. Check USB connection.")
        return
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("[ERROR] Could not read frame from camera.")
        return
    print("[OK] Camera is ready.\n")
    
    print(f"Connecting to Magician Lite on {PORT} ...")
    try:
        device = Dobot(port=PORT, verbose=False)
        print("[OK] Connected!")
        setup_speed(device, velocity=60, acceleration=30)
        
        # 1. Homing first
        print("\nHoming robot...")
        send_home(device)
        print("[OK] Home done.")
        
        # 2. Go to scan position
        print(f"\nMoving to Scan Position: X={SCAN_X}, Y={SCAN_Y}, Z={SCAN_Z} ...")
        device.move_to(SCAN_X, SCAN_Y, SCAN_Z, SCAN_R, wait=False)
        time.sleep(3.0)
        
        pts_pixel = []
        pts_robot = []
        
        # We need 3 points for affine transform
        for i in range(1, 4):
            print(f"\n--- CALIBRATION POINT {i}/3 ---")
            print("1. Place the RED block on the mat in the camera view.")
            input("   Press [Enter] when the block is in position to capture...")
            
            # Capture frame
            cap = cv2.VideoCapture(CAMERA_INDEX)
            time.sleep(0.5) # let camera adjust exposure
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                print("   [ERROR] Failed to capture frame. Let's try this point again.")
                continue
                
            center = detect_red_block(frame)
            if center is None:
                print("   [ERROR] Could not find the RED block in the image. Check lighting / placement.")
                # Save the image to debug
                cv2.imwrite("failed_calibration_detect.jpg", frame)
                print("   Saved snapshot to 'failed_calibration_detect.jpg' for inspection.")
                # Allow retry
                i -= 1
                continue
                
            u, v = center
            print(f"   [OK] Detected RED block at pixel coordinate: u={u}, v={v}")
            
            # Instruct user to guide the arm
            print("2. Press the unlock button on the arm (or forearm) to release the motors.")
            print("3. Physically move the arm so the suction cup is centered right on top of the block.")
            print("4. Lightly press it down to touch the block.")
            input("   Press [Enter] here once the arm is aligned...")
            
            # Read pose
            pose = read_stable_pose(device)
            if pose is None:
                print("   [ERROR] Could not read arm position. Let's try this point again.")
                i -= 1
                continue
                
            x_rob, y_rob = pose[0], pose[1]
            print(f"   [OK] Recorded Robot Pose: X={x_rob:.2f} mm, Y={y_rob:.2f} mm")
            
            pts_pixel.append([u, v])
            pts_robot.append([x_rob, y_rob])
            
            # Move arm back to scan position so it's ready for next capture
            print("\nRe-centering arm to Scan Position...")
            device.move_to(SCAN_X, SCAN_Y, SCAN_Z, SCAN_R, wait=False)
            time.sleep(3.0)
            
        # Calculate transform matrix
        src = np.float32(pts_pixel)
        dst = np.float32(pts_robot)
        
        print("\nCalculating calibration matrix...")
        matrix = cv2.getAffineTransform(src, dst)
        
        # Save to file
        calib_data = {
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
        
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "calibration.json"))
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
        try:
            device.close()
            print("Disconnected from Dobot.")
        except Exception:
            pass

if __name__ == "__main__":
    main()
