"""
test_distance_time.py
=====================
Tests a combined move+rotate sequence using the CORRECT blocking APIs.

PREVIOUS BUG: Used set_move_speed() + time.sleep() for both movement
and rotation. That approach is unreliable because:
  - set_move_speed is non-blocking (robot might not finish in time)
  - timing is not accurate (depends on surface friction)

FIXED: Now uses set_move_dist (blocking distance move) and
set_rotate (blocking angle turn) which wait until completion.
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

    # Reset odometer at start
    go.set_odometer_data(0, 0, 0)
    time.sleep(0.3)
    print("Odometer reset to (0, 0, 0)")

    # ── Step 1: Move forward 150 mm ───────────────────────────────────────────
    print("\n[1] Moving FORWARD 150 mm at 50 mm/s (blocking)...")
    go.set_move_dist(150, 0, 50, 0)
    pos = go.get_odometer_data()
    print(f"    Done. Odometer: X={pos['x']:.1f}  Y={pos['y']:.1f}  Yaw={pos['yaw']:.1f}°")
    time.sleep(0.5)

    # ── Step 2: Rotate LEFT 90° ───────────────────────────────────────────────
    print("\n[2] Rotating LEFT 90° at 40 deg/s (blocking)...")
    go.set_rotate(90, 40)   # positive = left/CCW
    pos = go.get_odometer_data()
    print(f"    Done. Odometer: X={pos['x']:.1f}  Y={pos['y']:.1f}  Yaw={pos['yaw']:.1f}°")
    time.sleep(0.5)

    # ── Step 3: Move forward 150 mm ───────────────────────────────────────────
    print("\n[3] Moving FORWARD 150 mm at 50 mm/s (blocking)...")
    go.set_move_dist(150, 0, 50, 0)
    pos = go.get_odometer_data()
    print(f"    Done. Odometer: X={pos['x']:.1f}  Y={pos['y']:.1f}  Yaw={pos['yaw']:.1f}°")
    time.sleep(0.5)

    # ── Step 4: Rotate RIGHT 90° (back to original heading) ──────────────────
    print("\n[4] Rotating RIGHT 90° at 40 deg/s (blocking)...")
    go.set_rotate(-90, 40)  # negative = right/CW
    pos = go.get_odometer_data()
    print(f"    Done. Odometer: X={pos['x']:.1f}  Y={pos['y']:.1f}  Yaw={pos['yaw']:.1f}°")
    time.sleep(0.5)

    # ── Step 5: Return to start ───────────────────────────────────────────────
    print("\n[5] Returning to start: moving BACKWARD 150 mm ...")
    go.set_move_dist(-150, 0, 50, 0)
    pos = go.get_odometer_data()
    print(f"    Done. Odometer: X={pos['x']:.1f}  Y={pos['y']:.1f}  Yaw={pos['yaw']:.1f}°")

    print("\n[OK]  All movement steps complete!")

except KeyboardInterrupt:
    print("\nInterrupted – stopping.")
    go.set_move_speed(0, 0, 0)

except Exception as e:
    import traceback
    print("\n[ERROR]  Error:")
    traceback.print_exc()
    try:
        go.set_move_speed(0, 0, 0)
    except Exception:
        pass
