"""
vision_pick_place.py
====================
Main vision-guided pick-and-place application.

Features:
  - Detects Red, Yellow, Blue, Green blocks using OpenCV HSV thresholding.
  - Transforms pixel centroids to physical robot (X, Y) using 'calibration.json'.
  - --preview flag: Run vision detection only, saving frame as 'preview.jpg'
                    in artifacts directory (no robot movement).
  - --color: Target specific color (red/yellow/blue/green/all).
  - --stack: Stack blocks of the same color at their target bin.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import os
import sys
import json
import time
import argparse
import cv2
import numpy as np
from pydobot import Dobot
from core.lite_move import setup_speed, move_to, send_home, suction_on, suction_off, gripper_open, gripper_close

PORT = "COM8"
CAMERA_INDEX = 0

# Fixed high-clearance Scan Position (must match calibration.py scan position!)
# Set to match the official Home coordinates (X=241.02, Y=0.00, Z=149.33, R=0.00)
SCAN_X, SCAN_Y, SCAN_Z, SCAN_R = 241.0, 0.0, 149.3, 0.0

# Base table Z height for pick-up
PICK_Z = -48.2
# Hover height during travel
Z_HOVER = 80.0
# Block height for stacking (in mm)
BLOCK_HEIGHT = 25.0

# Drop targets for sorting by color
DROP_TARGETS = {
    "red":    {"x": 280.0, "y": 120.0,  "z": -48.0, "r": 0.0},
    "yellow": {"x": 280.0, "y": 60.0,   "z": -48.0, "r": 0.0},
    "blue":   {"x": 280.0, "y": -60.0,  "z": -48.0, "r": 0.0},
    "green":  {"x": 280.0, "y": -120.0, "z": -48.0, "r": 0.0}
}

# Keep track of stack heights per color
STACK_COUNTS = {
    "red": 0,
    "yellow": 0,
    "blue": 0,
    "green": 0
}

# Define HSV color boundaries (Hue, Saturation, Value)
# Saturation bounds are set high (>=140) to ignore lower-saturation mat prints
COLOR_RANGES = {
    "red": [
        {"lower": np.array([0, 150, 80]),   "upper": np.array([10, 255, 255])},
        {"lower": np.array([165, 150, 80]), "upper": np.array([180, 255, 255])}
    ],
    "yellow": [
        {"lower": np.array([18, 140, 100]), "upper": np.array([32, 255, 255])}
    ],
    "green": [
        {"lower": np.array([40, 150, 60]),  "upper": np.array([85, 255, 255])}
    ],
    "blue": [
        {"lower": np.array([95, 150, 60]),  "upper": np.array([125, 255, 255])}
    ]
}

# BGR colors for drawing annotations
DRAW_COLORS = {
    "red": (0, 0, 255),
    "yellow": (0, 255, 255),
    "green": (0, 255, 0),
    "blue": (255, 0, 0)
}

# Region of Interest (ROI) inside the calibration mat grid
# (Ignores the green border at the top and the robot base at the bottom)
ROI_Y_MIN = 100
ROI_Y_MAX = 410
ROI_X_MIN = 50
ROI_X_MAX = 600

def detect_blocks(img, target_color="all"):
    """
    Scans the frame for blocks of the target color(s) within the ROI.
    Returns list of dicts: {"color": str, "center": (u,v), "area": float, "contour": cnt}
    """
    # Crop to Region of Interest (ROI)
    roi = img[ROI_Y_MIN:ROI_Y_MAX, ROI_X_MIN:ROI_X_MAX]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    detected = []
    
    colors_to_scan = [target_color] if target_color != "all" else ["red", "yellow", "green", "blue"]
    
    for color in colors_to_scan:
        mask = None
        for r in COLOR_RANGES[color]:
            m = cv2.inRange(hsv, r["lower"], r["upper"])
            if mask is None:
                mask = m
            else:
                mask = cv2.bitwise_or(mask, m)
                
        # Noise cleanup
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Sane block area limits (e.g. 300 to 5000 pixels)
            if 300 < area < 5000:
                # Bounding box constraints to verify it is a small square block
                x_box, y_box, w_box, h_box = cv2.boundingRect(cnt)
                
                # Sane width/height range: 20px to 100px
                if (20 <= w_box <= 100) and (20 <= h_box <= 100):
                    aspect_ratio = float(w_box) / h_box
                    # Sane aspect ratio range: 0.5 to 2.0
                    if 0.5 <= aspect_ratio <= 2.0:
                        M = cv2.moments(cnt)
                        if M['m00'] != 0:
                            cx = int(M['m10'] / M['m00'])
                            cy = int(M['m01'] / M['m00'])
                            
                            # Shift coordinates from ROI-relative back to original frame
                            cx_global = cx + ROI_X_MIN
                            cy_global = cy + ROI_Y_MIN
                            
                            # Shift contour points to global coordinates for correct visual drawing
                            cnt_global = cnt.copy()
                            cnt_global[:, 0, 0] += ROI_X_MIN
                            cnt_global[:, 0, 1] += ROI_Y_MIN
                            
                            detected.append({
                                "color": color,
                                "center": (cx_global, cy_global),
                                "area": area,
                                "contour": cnt_global
                            })
    return detected

def check_safety_bounds(x, y):
    """Verifies calculated X, Y are in a safe workspace bounding box."""
    # Magician Lite Reach limits:
    # Radius must be between 160mm and 340mm
    radius = np.sqrt(x**2 + y**2)
    in_range = (160.0 <= radius <= 340.0) and (150.0 <= x <= 340.0) and (-170.0 <= y <= 170.0)
    return in_range

def calculate_block_angle(cnt, matrix):
    """
    Calculates the rotation angle of the square block in physical robot coordinates.
    Maps it to the [-45, 45] range.
    """
    rect = cv2.minAreaRect(cnt)
    box = cv2.boxPoints(rect)
    
    # Transform pixel corners to robot physical coordinates
    pts = np.float32(box).reshape(-1, 1, 2)
    trans_pts = cv2.transform(pts, matrix).reshape(-1, 2)
    
    # Calculate angle of the first side in robot space
    p0, p1 = trans_pts[0], trans_pts[1]
    angle = np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))
    
    # Map to [-45, 45] range for square symmetry
    while angle > 45.0:
        angle -= 90.0
    while angle < -45.0:
        angle += 90.0
        
    return angle

def load_calibration():
    """Loads affine calibration data from calibration.json."""
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "calibration.json"))
    if not os.path.exists(config_path):
        print(f"[ERROR] Calibration file '{config_path}' not found!")
        print("Please run: python magician_lite/calibration.py")
        sys.exit(1)
        
    with open(config_path, "r") as f:
        data = json.load(f)
    return np.array(data["affine_matrix"])

def run_preview(target_color):
    """Captures frames in a loop, performs detection, and saves to preview.jpg."""
    out_dir = r"C:\Users\Admin\.gemini\antigravity\brain\474b5391-bf3e-4ea8-aeef-b9d90334d646"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "preview.jpg")
    
    print(f"Starting vision preview mode (target: {target_color})...")
    print(f"Viewing frame will save continuously to: {out_path}")
    print("Press Ctrl+C in terminal to exit.")
    
    # Try loading calibration matrix to annotate with robot coordinates
    matrix = None
    try:
        matrix = load_calibration()
        print("[INFO] Calibration loaded. Robot coordinates will be displayed.")
    except SystemExit:
        print("[WARN] No calibration.json found. Showing pixels only.")
        
    try:
        while True:
            cap = cv2.VideoCapture(CAMERA_INDEX)
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                print("[WARN] Failed to read camera frame. Retrying in 1s...")
                time.sleep(1.0)
                continue
                
            # Draw the scanning ROI boundary box (light gray)
            cv2.rectangle(frame, (ROI_X_MIN, ROI_Y_MIN), (ROI_X_MAX, ROI_Y_MAX), (220, 220, 220), 1)
            cv2.putText(frame, "ACTIVE SCAN ROI", (ROI_X_MIN + 5, ROI_Y_MIN + 15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (220, 220, 220), 1)

            blocks = detect_blocks(frame, target_color)
            
            # Annotate the image
            for b in blocks:
                color = b["color"]
                u, v = b["center"]
                cnt = b["contour"]
                
                # Draw bounding box
                x_box, y_box, w_box, h_box = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x_box, y_box), (x_box+w_box, y_box+h_box), DRAW_COLORS[color], 2)
                cv2.circle(frame, (u, v), 5, (0, 0, 255), -1)
                
                label = f"{color.upper()} ({u},{v})"
                if matrix is not None:
                    # Compute robot coordinates
                    pts = np.float32([[[u, v]]])
                    trans = cv2.transform(pts, matrix)
                    x_r, y_r = trans[0][0]
                    # Compute robot angle
                    pick_r = calculate_block_angle(cnt, matrix)
                    safe = "OK" if check_safety_bounds(x_r, y_r) else "OUT OF BOUNDS"
                    label += f" -> Rob: X={x_r:.1f}, Y={y_r:.1f}, R={pick_r:.1f} ({safe})"
                    
                cv2.putText(frame, label, (x_box, y_box-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, DRAW_COLORS[color], 1)
                
            cv2.imwrite(out_path, frame)
            print(f"[{time.strftime('%H:%M:%S')}] Detected {len(blocks)} blocks. Saved preview.")
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\nPreview stopped.")

def main():
    parser = argparse.ArgumentParser(description="Dobot Magician Lite Vision Pick & Place")
    parser.add_argument("--preview", action="store_true", help="Run in vision-only mode and write preview.jpg")
    parser.add_argument("--color", type=str, default="all", choices=["red", "yellow", "green", "blue", "all"],
                        help="Target block color (default: all)")
    parser.add_argument("--stack", action="store_true", help="Stack blocks of the same color")
    parser.add_argument("--gripper", action="store_true", help="Use gripper end-effector instead of suction cup")
    parser.add_argument("--pick-z", type=float, default=None, help="Custom pick height Z (default: -48.2 for suction, 10.0 for gripper)")
    args = parser.parse_args()
    
    if args.preview:
        run_preview(args.color)
        return
        
    # Load calibration matrix
    matrix = load_calibration()
    
    # Load drop targets from json if taught, otherwise fallback to defaults
    drop_targets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "drop_targets.json"))
    if os.path.exists(drop_targets_path):
        try:
            with open(drop_targets_path, "r") as f:
                drop_targets = json.load(f)
            print("[INFO] Loaded custom drop targets from drop_targets.json")
        except Exception as e:
            print(f"[WARN] Error reading drop_targets.json: {e}. Using defaults.")
            drop_targets = DROP_TARGETS
    else:
        drop_targets = DROP_TARGETS
        print("[INFO] drop_targets.json not found, using default coordinates.")
        
    # Set default pick Z based on end-effector selection
    if args.pick_z is not None:
        pick_z = args.pick_z
    else:
        pick_z = 10.0 if args.gripper else -48.2
    print(f"[INFO] Using end-effector: {'GRIPPER' if args.gripper else 'SUCTION CUP'} (Pick Z = {pick_z:.1f})")

    print(f"Connecting to Magician Lite on {PORT} ...")
    try:
        device = Dobot(port=PORT, verbose=False)
        print("[OK] Connected!")
        # Fast, smooth joint interpolation setup
        setup_speed(device, velocity=100, acceleration=60)
        
        # 1. Homing first
        print("\nHoming robot...")
        send_home(device)
        print("[OK] Home done.")
        
        # 2. Move to Scan Position (Home) once to capture frame
        print(f"\nMoving to Scan Position (Home) to scan ...")
        move_to(device, SCAN_X, SCAN_Y, SCAN_Z, SCAN_R)
        time.sleep(1.0) # let camera adjust exposure
        
        # Capture photo
        cap = cv2.VideoCapture(CAMERA_INDEX)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print("[ERROR] Camera failed to capture frame. Exiting...")
            return
            
        blocks = detect_blocks(frame, args.color)
        if not blocks:
            print(f"No {args.color} blocks detected. Scan complete. Exiting...")
            return
            
        print(f"\n[OK] Detected {len(blocks)} blocks: " + ", ".join([b["color"].upper() for b in blocks]))
        
        # Draw annotations on the captured frame to display to the user
        annotated_frame = frame.copy()
        # Draw ROI box
        cv2.rectangle(annotated_frame, (ROI_X_MIN, ROI_Y_MIN), (ROI_X_MAX, ROI_Y_MAX), (220, 220, 220), 1)
        cv2.putText(annotated_frame, "ACTIVE SCAN ROI", (ROI_X_MIN + 5, ROI_Y_MIN + 15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (220, 220, 220), 1)
                    
        for b in blocks:
            color = b["color"]
            u, v = b["center"]
            cnt = b["contour"]
            
            # Draw bounding box
            x_box, y_box, w_box, h_box = cv2.boundingRect(cnt)
            cv2.rectangle(annotated_frame, (x_box, y_box), (x_box+w_box, y_box+h_box), DRAW_COLORS[color], 2)
            cv2.circle(annotated_frame, (u, v), 5, (0, 0, 255), -1)
            
            # Label with robot coordinates
            label = f"{color.upper()} ({u},{v})"
            pts = np.float32([[[u, v]]])
            trans = cv2.transform(pts, matrix)
            x_r, y_r = trans[0][0]
            pick_r = calculate_block_angle(cnt, matrix)
            label += f" -> Rob: X={x_r:.1f}, Y={y_r:.1f}, R={pick_r:.1f}"
            
            cv2.putText(annotated_frame, label, (x_box, y_box-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, DRAW_COLORS[color], 1)
                        
        # Save the scanned image locally for reference
        run_img_path = os.path.join(os.path.dirname(__file__), "scanned_run.jpg")
        cv2.imwrite(run_img_path, annotated_frame)
        print(f"[INFO] Scanned image saved to {run_img_path}")
        
        # Display the window on desktop
        try:
            cv2.imshow("Scanned Workspace - Dobot Vision", annotated_frame)
            print("Displaying scanned image on desktop. Close window or wait 3 seconds to continue...")
            cv2.waitKey(3000)
            cv2.destroyAllWindows()
        except Exception as e:
            print(f"[WARN] Could not display GUI window: {e}")
            
        # Loop and pick each block
        for idx, block in enumerate(blocks):
            color = block["color"]
            u, v = block["center"]
            print(f"\n--- Processing Block {idx+1}/{len(blocks)} [{color.upper()}] ---")
            print(f"Target centroid: pixel u={u}, v={v}")
            
            # Map pixel coordinates to robot coordinates
            pts = np.float32([[[u, v]]])
            trans = cv2.transform(pts, matrix)
            x_robot, y_robot = trans[0][0]
            
            # Calculate block orientation angle
            pick_r = calculate_block_angle(block["contour"], matrix)
            
            print(f"Calculated Robot Position: X={x_robot:.2f} mm, Y={y_robot:.2f} mm, R={pick_r:.2f} deg")
            
            # Verify coordinates are safe to reach
            if not check_safety_bounds(x_robot, y_robot):
                print(f"[SAFETY WARNING] Calculated position ({x_robot:.1f}, {y_robot:.1f}) is out of safe range!")
                print("Skipping block to prevent collision.")
                continue
                
            # --- PICK SEQUENCE ---
            # A. Move above pick position
            print(f"  Moving above object (hover) with rotation R={pick_r:.1f} deg ...")
            move_to(device, x_robot, y_robot, Z_HOVER, pick_r)
            
            # B. Descend to pick height
            print(f"  Descending to pick object...")
            move_to(device, x_robot, y_robot, pick_z, pick_r)
            
            # C. Grasp (suction or gripper)
            if args.gripper:
                print(f"  Closing gripper...")
                gripper_close(device)
            else:
                print(f"  Suction ON...")
                suction_on(device)
            
            # D. Lift up
            print(f"  Lifting object...")
            move_to(device, x_robot, y_robot, Z_HOVER, pick_r)
            
            # --- PLACE SEQUENCE ---
            target = drop_targets[color]
            drop_x = target["x"]
            drop_y = target["y"]
            drop_z = target["z"]
            
            if args.stack:
                # Add offset based on how many blocks of this color have been stacked
                count = STACK_COUNTS[color]
                drop_z = target["z"] + (count * BLOCK_HEIGHT)
                print(f"  Stack mode enabled: Place index {count} for {color} (Z={drop_z:.1f})")
                
            # A. Move above place target
            print(f"  Moving above drop target...")
            move_to(device, drop_x, drop_y, Z_HOVER, target["r"])
            
            # B. Descend to drop height
            print(f"  Descending to drop target...")
            move_to(device, drop_x, drop_y, drop_z, target["r"])
            
            # C. Release (suction or gripper)
            if args.gripper:
                print(f"  Opening gripper...")
                gripper_open(device)
            else:
                print(f"  Suction OFF...")
                suction_off(device)
            
            # D. Lift away
            print(f"  Lifting away...")
            move_to(device, drop_x, drop_y, Z_HOVER, target["r"])
            
            if args.stack:
                STACK_COUNTS[color] += 1
                
            print(f"[OK] Completed pick and place cycle for {color} block.")
            
        print("\nAll target blocks processed. Returning home...")
        send_home(device)
        print("[SUCCESS] Process complete.")
        
    except Exception as e:
        print(f"\n[ERROR] System encountered an error: {e}")
        import traceback
        traceback.print_exc()
        try:
            if args.gripper: gripper_open(device)
            else: suction_off(device)
        except Exception: pass
    finally:
        try:
            # Kill pump completely
            from pydobot.message import Message
            msg = Message()
            msg.id     = 62
            msg.ctrl   = 0x03
            msg.params = bytearray([0x00, 0x00])
            device._send_command(msg)
            time.sleep(0.3)
            device._send_command(msg)
            device.close()
            print("Pump OFF. Disconnected.")
        except Exception:
            pass

if __name__ == "__main__":
    main()
