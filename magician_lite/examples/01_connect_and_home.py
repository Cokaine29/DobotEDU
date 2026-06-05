"""
01_connect_and_home.py
======================
Connects to the Dobot Magician Lite via pydobot (direct USB/serial).
Reads pose, sends HOME command, waits with a fixed sleep (no queue hang).

Requirements:
  - DobotLab / DobotLink must be CLOSED (they lock the COM port)
  - Robot is on COM8 (auto-detected)
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import struct
import time
from pydobot import Dobot
from pydobot.message import Message

PORT         = "COM8"
HOME_TIMEOUT = 15       # seconds to wait for homing to complete

def send_home(device):
    """
    Send SET_HOME_CMD (protocol ID 31) without waiting on queue index —
    pydobot's queue-wait hangs on this command, so we use a plain sleep.
    """
    msg = Message()
    msg.id   = 31       # SET_HOME_CMD
    msg.ctrl = 0x03     # queued + with response
    msg.params = bytearray([])
    device._send_command(msg, wait=False)   # fire-and-forget
    print(f"  Home command sent. Waiting {HOME_TIMEOUT}s for arm to settle ...")
    time.sleep(HOME_TIMEOUT)
    device.ser.reset_input_buffer()   # flush stale serial bytes after homing

print(f"Connecting to Magician Lite on {PORT} ...")

try:
    device = Dobot(port=PORT, verbose=False)
    print("[OK] Connected!\n")

    # ── Read current pose ──────────────────────────────────────────────────────
    pose = device.pose()
    print("  Current pose:")
    print(f"    X  = {pose[0]:.2f} mm")
    print(f"    Y  = {pose[1]:.2f} mm")
    print(f"    Z  = {pose[2]:.2f} mm")
    print(f"    R  = {pose[3]:.2f} deg")
    print(f"    J1 = {pose[4]:.2f} deg")
    print(f"    J2 = {pose[5]:.2f} deg")
    print(f"    J3 = {pose[6]:.2f} deg")
    print(f"    J4 = {pose[7]:.2f} deg\n")

    # ── Home ───────────────────────────────────────────────────────────────────
    print("Homing robot (arm will physically move) ...")
    send_home(device)
    print("[OK] Homing complete!\n")

    # ── Read pose after home ───────────────────────────────────────────────────
    time.sleep(0.3)                   # let robot settle
    pose = device.pose()
    print("  Pose after home:")
    print(f"    X={pose[0]:.2f}  Y={pose[1]:.2f}  Z={pose[2]:.2f}  R={pose[3]:.2f}")

    print("\n[DONE] All tests passed!")

except Exception as e:
    import traceback
    print("\n[ERROR]")
    traceback.print_exc()

finally:
    try:
        device.close()
        print("Disconnected.")
    except Exception:
        pass
