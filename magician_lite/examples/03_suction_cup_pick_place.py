"""
03_suction_cup_pick_place.py
============================
Suction cup pick and place for the Dobot Magician Lite.

SETUP GUIDE (do this before running):
  1. Place your object on the table in front of the robot
  2. Set PICK_X, PICK_Y to approximately where the object is
  3. Set PLACE_X, PLACE_Y to where you want to drop it
  4. Run with PREVIEW_ONLY = True first — arm shows hover positions only
  5. Check the positions look right, then set PREVIEW_ONLY = False to run for real
  6. Tune PICK_Z (lower = descend more to the object surface)

COORDINATE TIPS for Magician Lite:
  X: 180-260mm  (forward reach from robot base)
  Y: -80 to 80mm  (negative = right side, positive = left side)
  Z: keep above 50mm for safety
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from pydobot import Dobot
from core.lite_move import move_to, send_home, suction_on, suction_off

PORT = "COM8"

# ── CONFIGURE THESE FOR YOUR SETUP ───────────────────────────────────────────
PREVIEW_ONLY = True    # True = just show hover positions, False = full pick & place

PICK_X  = 220          # X position of the object (mm)
PICK_Y  = 0            # Y position of the object (mm)
PICK_Z  = 80           # Z to descend to for picking (tune this! lower = closer to table)

PLACE_X = 220          # X position of the drop bin (mm)
PLACE_Y = 80           # Y position of the drop bin (mm)
PLACE_Z = 80           # Z to descend to for placing

Z_HOVER = 130          # safe travel height between all moves (mm)
# ─────────────────────────────────────────────────────────────────────────────

print(f"Connecting to Magician Lite on {PORT} ...")
try:
    device = Dobot(port=PORT, verbose=False)
    print("[OK] Connected!\n")
    device.speed(velocity=40, acceleration=40)

    print("Homing ...")
    send_home(device)
    print("[OK] Home done\n")

    if PREVIEW_ONLY:
        print("=" * 50)
        print("  PREVIEW MODE — arm shows hover positions only")
        print("  Suction cup will NOT activate")
        print("=" * 50 + "\n")

        print(f"1. Moving to PICK hover  (X={PICK_X}, Y={PICK_Y}, Z={Z_HOVER}) ...")
        move_to(device, PICK_X, PICK_Y, Z_HOVER)
        print("   ^ This is above your pick object. Does it look right?")
        import time; time.sleep(2)

        print(f"\n2. Moving to PLACE hover (X={PLACE_X}, Y={PLACE_Y}, Z={Z_HOVER}) ...")
        move_to(device, PLACE_X, PLACE_Y, Z_HOVER)
        print("   ^ This is above your drop bin. Does it look right?")
        import time; time.sleep(2)

        move_to(device, 220, 0, Z_HOVER)
        print("\n[PREVIEW DONE]")
        print("If positions look good:")
        print("  1. Set PREVIEW_ONLY = False")
        print("  2. Tune PICK_Z / PLACE_Z to reach your object/bin surface")
        print("  3. Run again for real pick & place!")

    else:
        print("=" * 50)
        print("  LIVE MODE — full pick and place")
        print("=" * 50 + "\n")

        # ── PICK ──────────────────────────────────────────────────────────────
        print(f"1. Moving above pick  ({PICK_X}, {PICK_Y}, {Z_HOVER}) ...")
        move_to(device, PICK_X, PICK_Y, Z_HOVER)

        print(f"2. Descending to pick ({PICK_X}, {PICK_Y}, {PICK_Z}) ...")
        move_to(device, PICK_X, PICK_Y, PICK_Z)

        print("3. Activating suction cup ...")
        suction_on(device)

        print(f"4. Lifting object     ({PICK_X}, {PICK_Y}, {Z_HOVER}) ...")
        move_to(device, PICK_X, PICK_Y, Z_HOVER)

        # ── PLACE ─────────────────────────────────────────────────────────────
        print(f"5. Moving above place ({PLACE_X}, {PLACE_Y}, {Z_HOVER}) ...")
        move_to(device, PLACE_X, PLACE_Y, Z_HOVER)

        print(f"6. Descending to place ({PLACE_X}, {PLACE_Y}, {PLACE_Z}) ...")
        move_to(device, PLACE_X, PLACE_Y, PLACE_Z)

        print("7. Releasing suction cup ...")
        suction_off(device)

        print(f"8. Lifting away       ({PLACE_X}, {PLACE_Y}, {Z_HOVER}) ...")
        move_to(device, PLACE_X, PLACE_Y, Z_HOVER)

        print(f"9. Returning to safe position ...")
        move_to(device, 220, 0, Z_HOVER)

        print("\n[DONE] Pick and place complete!")

except Exception as e:
    import traceback
    try: suction_off(device)
    except Exception: pass
    print("\n[ERROR]"); traceback.print_exc()

finally:
    try: device.close(); print("Disconnected.")
    except Exception: pass
