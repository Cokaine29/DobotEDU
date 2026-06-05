"""
02_move_ptp.py
==============
Safe PTP movement test for the Dobot Magician Lite.

All waypoints are conservative and well within the reachable workspace:
  X = 220mm  (comfortable mid-reach)
  Y = -40 to +40mm  (small lateral moves only)
  Z = 100 to 130mm  (well above table, no risk of hitting anything)

HOW TO CALIBRATE FOR YOUR WORKSPACE:
  1. Run this script — watch the arm
  2. If it moves freely → increase range gradually
  3. If it struggles or skips → reduce range further
  4. Adjust X_MID, Y_RANGE, Z_HIGH, Z_LOW below to match your setup
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from pydobot import Dobot
from core.lite_move import move_to, send_home

PORT = "COM8"

# ── Tune these values for your robot's workspace ──────────────────────────────
X_MID   = 220    # comfortable forward reach (mm)
Y_RANGE = 40     # how far left/right to swing (mm)
Z_HIGH  = 130    # raised travel height (mm)
Z_LOW   = 100    # lower position (still safe above table)
# ─────────────────────────────────────────────────────────────────────────────

waypoints = [
    (X_MID,         0,       Z_HIGH,  0),   # centre, raised
    (X_MID,  +Y_RANGE,       Z_HIGH,  0),   # right
    (X_MID,  +Y_RANGE,       Z_LOW,   0),   # right, lower
    (X_MID,  -Y_RANGE,       Z_LOW,   0),   # left, lower
    (X_MID,  -Y_RANGE,       Z_HIGH,  0),   # left, raised
    (X_MID,         0,       Z_HIGH,  0),   # back to centre
]

print(f"Connecting to Magician Lite on {PORT} ...")
try:
    device = Dobot(port=PORT, verbose=False)
    print("[OK] Connected!\n")

    device.speed(velocity=40, acceleration=40)   # gentle speed

    print("Homing ...")
    send_home(device)
    print("[OK] Home done\n")

    print(f"Running {len(waypoints)} waypoints (conservative safe range) ...")
    print(f"  X={X_MID}mm | Y=±{Y_RANGE}mm | Z={Z_LOW}-{Z_HIGH}mm\n")

    for i, (x, y, z, r) in enumerate(waypoints):
        print(f"  [{i+1}/{len(waypoints)}] X={x}  Y={y:+}  Z={z}")
        move_to(device, x, y, z, r)
        print(f"         done")

    print("\n[DONE] All waypoints completed successfully!")

except Exception as e:
    import traceback
    print("\n[ERROR]"); traceback.print_exc()

finally:
    try: device.close(); print("Disconnected.")
    except Exception: pass
