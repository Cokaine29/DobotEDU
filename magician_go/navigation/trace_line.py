"""
trace_line.py
=============
Simple line-follower test. Place the GO on the black line and run this.
The robot will follow the line for 10 seconds then stop.

APIs used:
  go.set_trace_speed(speed)   - set line-following speed (5-50 recommended)
  go.set_auto_trace(True)     - start line following
  go.set_auto_trace(False)    - stop line following
"""
import time
from DobotEDU import dobot_edu

PORT = "COM4"

print(f"Connecting to Magician GO on {PORT}...")
dobot_edu.set_portname(PORT)
go = dobot_edu.magiciango

try:
    # Confirm connection
    battery = go.get_power_voltage()
    print(f"Connected! Battery: {battery['powerPercentage']:.0f}%")

    # Reset running mode to 0 (idle) first.
    # After using set_move_dist / set_rotate, the robot can get stuck
    # in a motion-queued mode where set_auto_trace is ignored.
    print("\nResetting running mode...")
    go.set_running_mode(0)
    time.sleep(0.3)

    # Set speed (20 is safe and stable on most track layouts)
    SPEED = 20
    print(f"Setting line-trace speed to {SPEED}...")
    go.set_trace_speed(SPEED)
    time.sleep(0.2)

    # Start line following
    print("Starting line follower. Place robot ON the black line!")
    print("Following for 10 seconds...\n")
    go.set_auto_trace(True)
    time.sleep(10)

    # Stop – always use this two-step sequence:
    # Step 1: set speed to 0
    # Step 2: disable auto-trace
    print("\nStopping...")
    go.set_trace_speed(0)
    time.sleep(0.3)
    go.set_auto_trace(False)
    print("[OK]  Stopped.")

except KeyboardInterrupt:
    print("\nInterrupted – stopping...")
    go.set_trace_speed(0)
    time.sleep(0.3)
    go.set_auto_trace(False)

except Exception as e:
    import traceback
    print("\n[ERROR]  Error:")
    traceback.print_exc()
    # Best-effort stop
    try:
        go.set_trace_speed(0)
        go.set_auto_trace(False)
    except Exception:
        pass
