"""
pick_and_place.py
=================
Single pick-and-place cycle for the Dobot Magician Lite.

Sequence:
  HOME → hover pick → descend → suction ON → lift →
  transit to drop → descend → suction OFF → lift → HOME

Positions from DobotLab:
  Pick  : X=242.4  Y=99.7   Z=-48.2  R=22.4
  Place : X=340.0  Y=-91.6  Z=-48.4  R=-15.1
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import time
from pydobot import Dobot
from core.lite_move import send_home, suction_on, suction_off, setup_speed, move_to

PORT = "COM8"

# ── Positions ─────────────────────────────────────────────────────────────────
PICK_X,  PICK_Y,  PICK_Z,  PICK_R  =  242.4,   99.7,  -48.2,  22.4
PLACE_X, PLACE_Y, PLACE_Z, PLACE_R =  340.0,  -91.6,  -48.4, -15.1

# Hover height for travel (high enough to clear any objects on the table)
# Pick/Place Z are both ~ -48mm, so 80mm hover = ~128mm clearance above surface
Z_HOVER = 80.0

# Move timing — 3.5s covers any move within the workspace at speed=40
MOVE_SLEEP = 3.5

# ── Helper ────────────────────────────────────────────────────────────────────
def move(device, x, y, z, r=0.0, label=""):
    if label:
        print(f"  {label}")
    device.move_to(x, y, z, r, wait=False)
    time.sleep(MOVE_SLEEP)

# ── Main ──────────────────────────────────────────────────────────────────────
print(f"Connecting to Magician Lite on {PORT} ...")
try:
    device = Dobot(port=PORT, verbose=False)
    print("[OK] Connected!\n")
    # velocity=80 (fast travel) + acceleration=40 (gentle ramp = no vibration)
    setup_speed(device, velocity=80, acceleration=40)

    # ── 1. Home ───────────────────────────────────────────────────────────────
    print("[1] Homing ...")
    send_home(device)
    print("    [OK] Home done\n")

    # ── 2. Move above pick (hover, wrist already at PICK_R) ───────────────────
    print("[2] Moving above pick position ...")
    move(device, PICK_X, PICK_Y, Z_HOVER, PICK_R,
         f"X={PICK_X}  Y={PICK_Y}  Z={Z_HOVER}  R={PICK_R}  (hover)")

    # ── 3. Descend to pick ────────────────────────────────────────────────────
    print("[3] Descending to object ...")
    move(device, PICK_X, PICK_Y, PICK_Z, PICK_R,
         f"X={PICK_X}  Y={PICK_Y}  Z={PICK_Z}  R={PICK_R}  (pick)")

    # ── 4. Suction ON ─────────────────────────────────────────────────────────
    print("[4] Activating suction cup ...")
    suction_on(device, delay=0.8)   # extra settle time to grip securely
    print("    Suction ON")

    # ── 5. Lift straight up (keep same X/Y/R) ─────────────────────────────────
    print("[5] Lifting object ...")
    move(device, PICK_X, PICK_Y, Z_HOVER, PICK_R,
         f"X={PICK_X}  Y={PICK_Y}  Z={Z_HOVER}  (lifted)")

    # ── 6. Transit to above drop (long swing ~215mm lateral) ─────────────────
    print("[6] Transiting to drop position ...")
    move(device, PLACE_X, PLACE_Y, Z_HOVER, PLACE_R,
         f"X={PLACE_X}  Y={PLACE_Y}  Z={Z_HOVER}  R={PLACE_R}  (hover)")

    # ── 7. Descend to drop ────────────────────────────────────────────────────
    print("[7] Descending to drop position ...")
    move(device, PLACE_X, PLACE_Y, PLACE_Z, PLACE_R,
         f"X={PLACE_X}  Y={PLACE_Y}  Z={PLACE_Z}  R={PLACE_R}  (place)")

    # ── 8. Suction OFF ────────────────────────────────────────────────────────
    print("[8] Releasing suction cup ...")
    suction_off(device, delay=0.6)
    print("    Suction OFF")

    # ── 9. Lift away from drop ────────────────────────────────────────────────
    print("[9] Lifting away ...")
    move(device, PLACE_X, PLACE_Y, Z_HOVER, PLACE_R,
         f"X={PLACE_X}  Y={PLACE_Y}  Z={Z_HOVER}  (lifted)")

    # ── 10. Home ─────────────────────────────────────────────────────────────
    print("[10] Returning home ...")
    send_home(device)
    print("     [OK] Home\n")

    print("=" * 40)
    print("  [DONE] Pick and place complete!")
    print("=" * 40)

except Exception as e:
    import traceback
    print("\n[ERROR]")
    try: suction_off(device)
    except Exception: pass
    traceback.print_exc()

finally:
    try:
        # Safety: kill pump completely with raw [0x00, 0x00] — NOT device.suck(False)
        # device.suck(False) sends [0x01, 0x00] which re-enables the end effector
        # and can restart the pump. [0x00, 0x00] = enable=OFF, pump=OFF.
        import time
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
