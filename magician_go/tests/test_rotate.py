"""
test_rotate.py
==============
Tests rotation using set_rotate.
This is a BLOCKING call – the script waits until the robot finishes rotating.

API:
  go.set_rotate(r, Vr)
    r  : angle to rotate in degrees
         positive = counter-clockwise (turn LEFT)
         negative = clockwise (turn RIGHT)
    Vr : rotational speed in deg/s  (use 30-60 for smooth rotation)

  NOTE: This is a queued, blocking command. No need for time.sleep() after it.
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

    # Reset odometer to track yaw
    go.set_odometer_data(0, 0, 0)
    time.sleep(0.3)

    # ── Turn LEFT 90° ─────────────────────────────────────────────────────────
    print("\nTurning LEFT 90° at 40 deg/s ...")
    go.set_rotate(90, 40)   # positive = CCW = left
    print("Left turn done.")

    pos = go.get_odometer_data()
    print(f"Yaw after left turn: {pos['yaw']:.1f}°  (expected ~90°)")

    time.sleep(1)

    # ── Turn RIGHT 90° (back to start) ────────────────────────────────────────
    print("\nTurning RIGHT 90° at 40 deg/s ...")
    go.set_rotate(-90, 40)  # negative = CW = right
    print("Right turn done.")

    pos = go.get_odometer_data()
    print(f"Yaw after right turn: {pos['yaw']:.1f}°  (expected ~0°)")

    print("\n[OK]  Rotation test done!")

except Exception as e:
    import traceback
    print("\n[ERROR]  Error:")
    traceback.print_exc()
