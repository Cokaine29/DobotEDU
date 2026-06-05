"""
vision_pick_place.py
====================
Main vision-guided sorting script for the Magician GO + Magician Lite combo.

Workflow:
  1. Move to Ground Scan Position (Home) to locate the target colored boxes on the ground.
  2. Move to Chassis Scan Position to locate the blocks stored on the chassis.
  3. Pick each block from the chassis and drop it in its corresponding colored box on the ground.

Usage:
  # Run in preview mode to verify camera detection
  python magician_go_lite/vision/vision_pick_place.py --preview --camera 0
  
  # Run standard sorting with suction cup
  python magician_go_lite/vision/vision_pick_place.py --port COM6 --camera 0
  
  # Run with gripper
  python magician_go_lite/vision/vision_pick_place.py --port COM6 --camera 0 --gripper --pick-z 35.0 --drop-z 15.0
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

# Scan positions
SCAN_CHASSIS = {"x": 0.0, "y": -241.9, "z": 66.8, "r": -90.0}
SCAN_GROUND  = {"x": 241.0, "y": 0.0,  "z": 149.3, "r": 0.0}

Z_HOVER = 80.0 # Hover height during travel

# Define HSV color boundaries (Hue, Saturation, Value)
COLOR_RANGES = {
    "red": [
        {"lower": np.array([0, 140, 80]),   "upper": np.array([10, 255, 255])},
        {"lower": np.array([165, 140, 80]), "upper": np.array([180, 255, 255])}
    ],
    "yellow": [
        {"lower": np.array([18, 130, 80]),  "upper": np.array([32, 255, 255])}
    ],
    "green": [
        {"lower": np.array([38, 140, 60]),  "upper": np.array([85, 255, 255])}
    ],
    "blue": [
        {"lower": np.array([95, 140, 60]),  "upper": np.array([125, 255, 255])}
    ]
}

DRAW_COLORS = {
    "red": (0, 0, 255),
    "yellow": (0, 255, 255),
    "green": (0, 255, 0),
    "blue": (255, 0, 0)
}

# Scan Regions of Interest (ROI)
# Ground Scan (Home position perspective)
GROUND_ROI = {"x_min": 50, "x_max": 600, "y_min": 100, "y_max": 410}

# Chassis Scan (Arm rotated to Y=-241.9 perspective)
CHASSIS_ROI = {"x_min": 50, "x_max": 600, "y_min": 100, "y_max": 410}

def load_calibration(filename):
    """Loads calibration matrix from magician_go_lite/config/."""
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", filename))
    if not os.path.exists(config_path):
        print(f"[ERROR] Calibration file '{config_path}' not found!")
        print("Please run: python magician_go_lite/vision/calibration.py --target [chassis/ground]")
        sys.exit(1)
        
    with open(config_path, "r") as f:
        data = json.load(f)
    return np.array(data["affine_matrix"])

def detect_objects(img, roi_bounds, is_box=False):
    """
    Detects blocks or boxes within the specified ROI.
    - is_box=False: Filters for small blocks (area: 300 to 5000)
    - is_box=True: Filters for larger boxes/squares (area: 5000 to 80000)
    """
    x_min, x_max = roi_bounds["x_min"], roi_bounds["x_max"]
    y_min, y_max = roi_bounds["y_min"], roi_bounds["y_max"]
    
    roi = img[y_min:y_max, x_min:x_max]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    detected = []
    
    # Area thresholds
    min_area = 5000 if is_box else 300
    max_area = 80000 if is_box else 5000
    
    for color in ["red", "yellow", "green", "blue"]:
        mask = None
        for r in COLOR_RANGES[color]:
            m = cv2.inRange(hsv, r["lower"], r["upper"])
            if mask is None:
                mask = m
            else:
                mask = cv2.bitwise_or(mask, m)
                
        # Clean up noise
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # If looking for boxes, we only want the largest contour of each color
        if is_box:
            box_contours = [c for c in contours if min_area < cv2.contourArea(c) < max_area]
            if box_contours:
                best_cnt = max(box_contours, key=cv2.contourArea)
                M = cv2.moments(best_cnt)
                if M['m00'] != 0:
                    cx = int(M['m10'] / M['m00']) + x_min
                    cy = int(M['m01'] / M['m00']) + y_min
                    
                    cnt_global = best_cnt.copy()
                    cnt_global[:, 0, 0] += x_min
                    cnt_global[:, 0, 1] += y_min
                    
                    detected.append({
                        "color": color,
                        "center": (cx, cy),
                        "area": cv2.contourArea(best_cnt),
                        "contour": cnt_global
                    })
        else:
            # Looking for blocks (multiple blocks of same color can exist)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if min_area < area < max_area:
                    x_b, y_b, w_b, h_b = cv2.boundingRect(cnt)
                    aspect_ratio = float(w_b) / h_b
                    if 0.5 <= aspect_ratio <= 2.0:
                        M = cv2.moments(cnt)
                        if M['m00'] != 0:
                            cx = int(M['m10'] / M['m00']) + x_min
                            cy = int(M['m01'] / M['m00']) + y_min
                            
                            cnt_global = cnt.copy()
                            cnt_global[:, 0, 0] += x_min
                            cnt_global[:, 0, 1] += y_min
                            
                            detected.append({
                                "color": color,
                                "center": (cx, cy),
                                "area": area,
                                "contour": cnt_global
                            })
                            
    return detected

def calculate_rotation_angle(cnt, matrix):
    """Calculates box/block rotation in robot space, mapping to [-45, 45]."""
    rect = cv2.minAreaRect(cnt)
    box = cv2.boxPoints(rect)
    pts = np.float32(box).reshape(-1, 1, 2)
    trans_pts = cv2.transform(pts, matrix).reshape(-1, 2)
    
    p0, p1 = trans_pts[0], trans_pts[1]
    angle = np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))
    
    while angle > 45.0:
        angle -= 90.0
    while angle < -45.0:
        angle += 90.0
    return angle

def check_safety_bounds(x, y):
    """Safety boundary check for Magician Lite workspace."""
    radius = np.sqrt(x**2 + y**2)
    return (160.0 <= radius <= 340.0) and (x >= 0)

def run_preview(camera_idx):
    """Preview mode to test camera feeds and overlay detections without robot movement."""
    out_dir = r"C:\Users\Admin\.gemini\antigravity\brain\474b5391-bf3e-4ea8-aeef-b9d90334d646"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "combo_preview.jpg")
    
    print("Starting vision preview mode...")
    print(f"Preview image will save continuously to: {out_path}")
    print("Press Ctrl+C to stop.")
    
    # Try loading calibrations
    mat_chassis = mat_ground = None
    try:
        mat_chassis = load_calibration("calibration_chassis.json")
        print("[INFO] Chassis calibration loaded.")
    except SystemExit:
        print("[WARN] calibration_chassis.json not found.")
    try:
        mat_ground = load_calibration("calibration_ground.json")
        print("[INFO] Ground calibration loaded.")
    except SystemExit:
        print("[WARN] calibration_ground.json not found.")
        
    try:
        while True:
            cap = cv2.VideoCapture(camera_idx)
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                print("[WARN] Failed to read frame. Retrying...")
                time.sleep(1.0)
                continue
                
            annotated = frame.copy()
            
            # Draw ground scan ROI (default preview assumes ground scan context first)
            cv2.rectangle(annotated, (GROUND_ROI["x_min"], GROUND_ROI["y_min"]), 
                          (GROUND_ROI["x_max"], GROUND_ROI["y_max"]), (220, 220, 220), 1)
            cv2.putText(annotated, "GROUND ROI", (GROUND_ROI["x_min"] + 5, GROUND_ROI["y_min"] + 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1)
            
            # Detect blocks (small) and boxes (large)
            blocks = detect_objects(frame, GROUND_ROI, is_box=False)
            boxes = detect_objects(frame, GROUND_ROI, is_box=True)
            
            # Annotate blocks
            for b in blocks:
                color = b["color"]
                u, v = b["center"]
                x_b, y_b, w_b, h_b = cv2.boundingRect(b["contour"])
                cv2.rectangle(annotated, (x_b, y_b), (x_b+w_b, y_b+h_b), DRAW_COLORS[color], 2)
                cv2.circle(annotated, (u, v), 4, (0, 0, 255), -1)
                
                label = f"BLOCK:{color.upper()} ({u},{v})"
                if mat_chassis is not None:
                    pts = np.float32([[[u, v]]])
                    trans = cv2.transform(pts, mat_chassis)
                    rx, ry = trans[0][0]
                    label += f" -> X={rx:.1f}, Y={ry:.1f}"
                cv2.putText(annotated, label, (x_b, y_b-5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, DRAW_COLORS[color], 1)
                
            # Annotate boxes
            for bx in boxes:
                color = bx["color"]
                u, v = bx["center"]
                x_b, y_b, w_b, h_b = cv2.boundingRect(bx["contour"])
                cv2.drawContours(annotated, [bx["contour"]], -1, DRAW_COLORS[color], 1) # dotted or thin line
                cv2.circle(annotated, (u, v), 8, (255, 255, 255), 1)
                
                label = f"BOX:{color.upper()} ({u},{v})"
                if mat_ground is not None:
                    pts = np.float32([[[u, v]]])
                    trans = cv2.transform(pts, mat_ground)
                    rx, ry = trans[0][0]
                    label += f" -> X={rx:.1f}, Y={ry:.1f}"
                cv2.putText(annotated, label, (x_b, y_b+h_b+15), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
                
            cv2.imwrite(out_path, annotated)
            print(f"[{time.strftime('%H:%M:%S')}] Detected {len(blocks)} blocks, {len(boxes)} boxes. Saved preview.")
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\nPreview stopped.")

def main():
    parser = argparse.ArgumentParser(description="Magician GO + Lite Combo Pick & Place")
    parser.add_argument("--preview", action="store_true", help="Run vision-only preview mode")
    parser.add_argument("--port", type=str, default="COM6", help="COM port for Magician Lite")
    parser.add_argument("--camera", type=int, default=0, help="USB camera index (default: 0)")
    parser.add_argument("--gripper", action="store_true", help="Use gripper instead of suction cup")
    parser.add_argument("--pick-z", type=float, default=None, help="Custom block pick height on chassis floor")
    parser.add_argument("--drop-z", type=float, default=None, help="Custom block drop height above ground boxes")
    args = parser.parse_args()
    
    if args.preview:
        run_preview(args.camera)
        return
        
    # Load calibrations
    print("Loading calibration files...")
    mat_chassis = load_calibration("calibration_chassis.json")
    mat_ground = load_calibration("calibration_ground.json")
    print("[OK] Calibrations loaded.")
    
    # Establish Z coordinates
    if args.pick_z is not None:
        pick_z = args.pick_z
    else:
        pick_z = 35.0 # default pick height from chassis floor
        
    if args.drop_z is not None:
        drop_z = args.drop_z
    else:
        drop_z = 15.0 if args.gripper else -35.0 # default drop height above ground boxes
        
    print(f"End-effector: {'GRIPPER' if args.gripper else 'SUCTION CUP'}")
    print(f"Pick Z (Chassis): {pick_z:.1f} mm | Drop Z (Ground): {drop_z:.1f} mm")
    
    lite = get_lite(args.port)
    try:
        safe_connect(lite)
        
        print("\nHoming robot...")
        lite.set_homecmd()
        print("[OK] Homing complete.")
        
        lite.set_ptpcommon_params(velocity_ratio=80, acceleration_ratio=40)
        
        cap = cv2.VideoCapture(args.camera)
        if not cap.isOpened():
            print("[ERROR] Could not open camera.")
            return
            
        # ── STEP 1: Scan Ground Boxes ─────────────────────────────────────────
        print(f"\nMoving to Ground Scan Position: X={SCAN_GROUND['x']}, Y={SCAN_GROUND['y']}...")
        move_to(lite, SCAN_GROUND['x'], SCAN_GROUND['y'], SCAN_GROUND['z'], SCAN_GROUND['r'])
        time.sleep(1.0) # let camera adjust exposure
        
        # Flush buffer and read
        for _ in range(5): cap.read()
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Camera failed to capture ground image.")
            cap.release()
            return
            
        ground_boxes = detect_objects(frame, GROUND_ROI, is_box=True)
        if not ground_boxes:
            print("[ERROR] No target color boxes detected on the ground! Cannot proceed.")
            cap.release()
            return
            
        print(f"[OK] Detected {len(ground_boxes)} target boxes on ground:")
        box_coords = {}
        for box in ground_boxes:
            color = box["color"]
            u, v = box["center"]
            pts = np.float32([[[u, v]]])
            trans = cv2.transform(pts, mat_ground)
            bx, by = trans[0][0]
            box_angle = calculate_rotation_angle(box["contour"], mat_ground)
            
            box_coords[color] = {"x": bx, "y": by, "r": box_angle}
            print(f"  - {color.upper()}: pixel ({u}, {v}) -> Robot X={bx:.1f}, Y={by:.1f}, R={box_angle:.1f}")
            
        # ── STEP 2: Scan Chassis Blocks ───────────────────────────────────────
        print(f"\nMoving to Chassis Scan Position: X={SCAN_CHASSIS['x']}, Y={SCAN_CHASSIS['y']}...")
        move_to(lite, SCAN_CHASSIS['x'], SCAN_CHASSIS['y'], SCAN_CHASSIS['z'], SCAN_CHASSIS['r'])
        time.sleep(1.0)
        
        # Flush buffer and read
        for _ in range(5): cap.read()
        ret, frame = cap.read()
        cap.release() # release camera, we are done scanning
        if not ret:
            print("[ERROR] Camera failed to capture chassis image.")
            return
            
        blocks = detect_objects(frame, CHASSIS_ROI, is_box=False)
        if not blocks:
            print("[INFO] No blocks detected on the chassis floor. Exiting...")
            return
            
        print(f"[OK] Detected {len(blocks)} blocks on chassis: " + ", ".join([b["color"].upper() for b in blocks]))
        
        # ── STEP 3: Pick and Place Sequence ───────────────────────────────────
        for idx, block in enumerate(blocks):
            color = block["color"]
            u, v = block["center"]
            print(f"\n--- Processing Block {idx+1}/{len(blocks)} [{color.upper()}] ---")
            
            # Map block pixel to robot coordinates using chassis calibration
            pts = np.float32([[[u, v]]])
            trans = cv2.transform(pts, mat_chassis)
            block_x, block_y = trans[0][0]
            block_angle = calculate_rotation_angle(block["contour"], mat_chassis)
            
            print(f"Block Chassis Pose: X={block_x:.1f}, Y={block_y:.1f}, R={block_angle:.1f}")
            
            # Verify block coordinates are safe
            if not check_safety_bounds(block_x, block_y):
                print(f"[SAFETY WARNING] Block coordinates ({block_x:.1f}, {block_y:.1f}) out of safe reach! Skipping.")
                continue
                
            # Verify drop target exists
            if color not in box_coords:
                print(f"[WARN] No target box detected for color '{color.upper()}'. Skipping block.")
                continue
                
            target_box = box_coords[color]
            drop_x = target_box["x"]
            drop_y = target_box["y"]
            drop_angle = target_box["r"]
            
            if not check_safety_bounds(drop_x, drop_y):
                print(f"[SAFETY WARNING] Box coordinates ({drop_x:.1f}, {drop_y:.1f}) out of safe reach! Skipping.")
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
            
            # B. Place Sequence (to ground box)
            print(f"  Hovering over target {color.upper()} box...")
            move_to(lite, drop_x, drop_y, Z_HOVER, drop_angle)
            
            print(f"  Descending to drop height Z={drop_z:.1f}...")
            move_to(lite, drop_x, drop_y, drop_z, drop_angle)
            
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
