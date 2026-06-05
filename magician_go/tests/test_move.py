"""
test_move.py
============
Tests basic straight-line movement using set_move_dist.
This is a BLOCKING call – the script will wait until the robot
has physically finished moving before continuing.

API:
  go.set_move_dist(x, y, Vx, Vy)
    x  : distance to move in X direction (forward = positive)   [mm]
    y  : distance to move in Y direction (sideways)             [mm]
    Vx : speed in X direction                                   [mm/s]
    Vy : speed in Y direction                                   [mm/s]

  NOTE: This is a queued, blocking command. The script pauses here
  until the movement is done. No need for time.sleep() after it.
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

    # Reset odometer so we can verify movement
    go.set_odometer_data(0, 0, 0)
    time.sleep(0.3)

    # ── Move forward 100 mm at 50 mm/s ───────────────────────────────────────
    print("\nMoving FORWARD 100 mm at 50 mm/s ...")
    go.set_move_dist(100, 0, 50, 0)
    print("Forward move complete.")

    pos = go.get_odometer_data()
    print(f"Odometer after forward: X={pos['x']:.1f}  Y={pos['y']:.1f}")

    time.sleep(1)

    # ── Move backward 100 mm at 50 mm/s ──────────────────────────────────────
    print("\nMoving BACKWARD 100 mm at 50 mm/s ...")
    go.set_move_dist(-100, 0, 50, 0)
    print("Backward move complete.")

    pos = go.get_odometer_data()
    print(f"Odometer after backward: X={pos['x']:.1f}  Y={pos['y']:.1f}")

    print("\n[OK]  Movement test done!")

except Exception as e:
    import traceback
    print("\n[ERROR]  Error:")
    traceback.print_exc()
