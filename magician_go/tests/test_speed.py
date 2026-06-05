"""
test_speed.py
=============
Tests set_move_speed – a CONTINUOUS (non-blocking) speed command.
Unlike set_move_dist, the robot keeps moving until you send speed=0.

API:
  go.set_move_speed(x, y, r)
    x : forward/backward speed  (positive = forward)  [mm/s]
    y : sideways speed          (positive = left)      [mm/s]
    r : rotation speed          (positive = CCW/left)  [deg/s]

  Use this for:
    - Fine real-time control while reading sensors in a loop
    - Emergency stop: go.set_move_speed(0, 0, 0)

  For precise distances, prefer set_move_dist (blocking).
  For precise angles,    prefer set_rotate    (blocking).
"""
import time
from DobotEDU import dobot_edu

PORT = "COM4"

print(f"Connecting to Magician GO on {PORT}...")
dobot_edu.set_portname(PORT)
go = dobot_edu.magiciango

try:
    battery = go.get_power_voltage()
    print(f"Connected! Battery: {battery['powerPercentage']:.0f}%")

    # ── Move forward at 30 mm/s for 2 seconds ────────────────────────────────
    print("\nSending continuous FORWARD speed: 30 mm/s for 2 seconds...")
    go.set_move_speed(30, 0, 0)
    time.sleep(2)
    go.set_move_speed(0, 0, 0)   # stop
    print("Stopped.")

    time.sleep(1)

    # ── Rotate left at 30 deg/s for 1 second ─────────────────────────────────
    print("\nSending continuous LEFT ROTATION: 30 deg/s for 1 second...")
    go.set_move_speed(0, 0, 30)
    time.sleep(1)
    go.set_move_speed(0, 0, 0)   # stop
    print("Stopped.")

    print("\n[OK]  Speed test done!")

except KeyboardInterrupt:
    print("\nInterrupted – stopping...")
    go.set_move_speed(0, 0, 0)

except Exception as e:
    import traceback
    print("\n[ERROR]  Error:")
    traceback.print_exc()
    try:
        go.set_move_speed(0, 0, 0)
    except Exception:
        pass
