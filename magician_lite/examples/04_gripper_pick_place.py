"""
04_gripper_pick_place.py
========================
Pick and place with gripper. Direct USB via pydobot.
Adjust PICK_POS, PLACE_POS, and Z_HOVER to your workspace.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from pydobot import Dobot
from core.lite_move import move_to, send_home, gripper_open, gripper_close

PORT      = "COM8"
Z_HOVER   = 70.0
PICK_POS  = (220.0,   0.0, 10.0, 0.0)
PLACE_POS = (150.0, 120.0, 10.0, 0.0)

print(f"Connecting on {PORT} ...")
try:
    device = Dobot(port=PORT, verbose=False)
    print("[OK] Connected!\n")
    device.speed(velocity=50, acceleration=50)

    print("Homing ..."); send_home(device); print("[OK] Home done\n")

    px, py, pz, pr = PICK_POS
    dx, dy, dz, dr = PLACE_POS

    print("1. Open gripper ..."); gripper_open(device)
    print("2. Above pick ..."); move_to(device, px, py, Z_HOVER, pr)
    print("3. Descend to pick ..."); move_to(device, px, py, pz, pr)
    print("4. Close gripper (grasp) ..."); gripper_close(device)
    print("5. Lift ..."); move_to(device, px, py, Z_HOVER, pr)
    print("6. Above place ..."); move_to(device, dx, dy, Z_HOVER, dr)
    print("7. Descend to place ..."); move_to(device, dx, dy, dz, dr)
    print("8. Open gripper (release) ..."); gripper_open(device)
    print("9. Lift away ..."); move_to(device, dx, dy, Z_HOVER, dr)
    print("10. Safe position ..."); move_to(device, 200.0, 0.0, Z_HOVER, 0.0)

    print("\n[DONE] Gripper pick and place complete!")

except Exception as e:
    import traceback
    try: gripper_open(device)
    except Exception: pass
    print("\n[ERROR]"); traceback.print_exc()

finally:
    try: device.close(); print("Disconnected.")
    except Exception: pass
