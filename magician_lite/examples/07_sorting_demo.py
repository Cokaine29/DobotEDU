"""
07_sorting_demo.py
==================
Simulated sorting demo for the Dobot Magician Lite.

Scenario:
  - Three "bins" are defined at fixed positions (e.g. for Red, Green, Blue).
  - A list of items describes what's at each pick slot and its colour.
  - The robot picks each item and places it in the correct colour bin.

This script is a template — adapt PICK_SLOTS, BIN_POSITIONS, and ITEMS
to match your real physical layout.

Requirements:
  - DobotLink must be running
  - Suction cup attached
  - Adjust PORT and positions as needed
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import time
from core.lite_helper import get_lite, safe_connect, safe_disconnect

# ── Configuration ─────────────────────────────────────────────────────────────
PORT    = "COM4"
Z_HOVER = 70.0    # safe travel height (mm)
Z_PICK  = 5.0     # height to pick up item (mm)
Z_PLACE = 5.0     # height to place item (mm)

# Pick slot positions  {slot_id: (X, Y)}
PICK_SLOTS = {
    1: (220.0,  40.0),
    2: (220.0,   0.0),
    3: (220.0, -40.0),
}

# Bin positions  {colour: (X, Y)}
BIN_POSITIONS = {
    "red":   (140.0,  90.0),
    "green": (160.0,   0.0),
    "blue":  (140.0, -90.0),
}

# Items to sort  [(slot_id, colour), ...]
ITEMS = [
    (1, "red"),
    (2, "blue"),
    (3, "green"),
    (2, "red"),    # second pass — can repeat slots
]

# ── Setup ─────────────────────────────────────────────────────────────────────
lite = get_lite(PORT)

def move(x, y, z, r=0.0, mode=1):
    lite.set_ptpcmd(ptp_mode=mode, x=x, y=y, z=z, r=r)

def suction(on: bool):
    lite.set_endeffector_suctioncup(enable=True, on=on)
    time.sleep(0.4)

def pick(x, y):
    """Descend, activate suction, lift."""
    move(x, y, Z_HOVER)
    move(x, y, Z_PICK)
    suction(True)
    move(x, y, Z_HOVER)

def place(x, y):
    """Descend to bin, release suction, lift."""
    move(x, y, Z_HOVER)
    move(x, y, Z_PLACE)
    suction(False)
    move(x, y, Z_HOVER)

# ── Main ───────────────────────────────────────────────────────────────────────
try:
    safe_connect(lite)
    print()

    print("Homing ...")
    lite.set_homecmd()
    print("[OK] Home done\n")

    lite.set_ptpcommon_params(velocity_ratio=50, acceleration_ratio=50)

    print(f"Sorting {len(ITEMS)} items ...\n")

    for i, (slot_id, colour) in enumerate(ITEMS, start=1):
        px, py = PICK_SLOTS[slot_id]
        bx, by = BIN_POSITIONS[colour]

        print(f"[{i}/{len(ITEMS)}] Picking from slot {slot_id} → '{colour}' bin")
        print(f"         Pick: ({px}, {py})  |  Bin: ({bx}, {by})")

        pick(px, py)
        place(bx, by)

        print(f"         ✓ Done\n")

    # Return to safe position
    move(200.0, 0.0, Z_HOVER)
    print("[DONE] Sorting complete!")

except Exception as e:
    import traceback
    try:
        suction(False)
    except Exception:
        pass
    print("\n[ERROR]")
    traceback.print_exc()

finally:
    safe_disconnect(lite)
