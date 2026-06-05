"""
test_gripper_rotation.py
========================
Diagnostic script to test the physical R-axis (wrist servo) rotation.

Workflow:
  1. Home the robot.
  2. Move to a safe hover position (X=220, Y=0, Z=100) with R=0.
  3. Rotate R to 45.0 degrees, then -45.0 degrees, then back to 0.
  4. Print the reported pose after each movement to check if the controller registers it.
"""

import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pydobot import Dobot
from core.lite_move import setup_speed, send_home, move_to

PORT = "COM8"

def read_pose(device):
    """Cleanly read the current pose."""
    for _ in range(5):
        time.sleep(0.1)
        device.ser.reset_input_buffer()
        pose = device.pose()
        if abs(pose[0]) < 1000 and abs(pose[1]) < 1000:
            return pose
    return None

def main():
    print("=== Dobot Magician Lite R-Axis Rotation Diagnostic ===")
    print("Ensure DobotLab is closed before running.\n")
    
    print(f"Connecting to Dobot on {PORT}...")
    try:
        device = Dobot(port=PORT, verbose=False)
        print("[OK] Connected!")
        setup_speed(device, velocity=50, acceleration=30)
        
        print("\n1. Homing...")
        send_home(device)
        print("[OK] Home done.")
        
        # Test coordinates
        x, y, z = 220.0, 0.0, 100.0
        
        # R=0
        print(f"\n2. Moving to X={x}, Y={y}, Z={z} with R=0.0 ...")
        move_to(device, x, y, z, 0.0)
        pose = read_pose(device)
        if pose:
            print(f"   Reported Pose: X={pose[0]:.1f}, Y={pose[1]:.1f}, Z={pose[2]:.1f}, R={pose[3]:.1f}")
            
        # R=45
        print(f"\n3. Rotating R to +45.0 degrees ...")
        move_to(device, x, y, z, 45.0)
        pose = read_pose(device)
        if pose:
            print(f"   Reported Pose: X={pose[0]:.1f}, Y={pose[1]:.1f}, Z={pose[2]:.1f}, R={pose[3]:.1f}")
            
        # R=-45
        print(f"\n4. Rotating R to -45.0 degrees ...")
        move_to(device, x, y, z, -45.0)
        pose = read_pose(device)
        if pose:
            print(f"   Reported Pose: X={pose[0]:.1f}, Y={pose[1]:.1f}, Z={pose[2]:.1f}, R={pose[3]:.1f}")
            
        # R=0
        print(f"\n5. Resetting R to 0.0 ...")
        move_to(device, x, y, z, 0.0)
        pose = read_pose(device)
        if pose:
            print(f"   Reported Pose: X={pose[0]:.1f}, Y={pose[1]:.1f}, Z={pose[2]:.1f}, R={pose[3]:.1f}")
            
        print("\nDiagnostic movements finished.")
        
    except Exception as e:
        print(f"\n[ERROR] Diagnostic encountered an issue: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            device.close()
            print("Disconnected.")
        except Exception:
            pass

if __name__ == "__main__":
    main()
