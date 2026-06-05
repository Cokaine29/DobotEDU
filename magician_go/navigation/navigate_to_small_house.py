"""
navigate_to_small_house.py  (and park_small_house.py combined)
==============================================================
Navigate the Dobot Magician GO from the start position (0,0)
to the Small House parking bay, following the road lines.

HOW IT WORKS
────────────
Phase 1 → Line follower ON  → robot drives along the bottom road
           Watch odometer X. When X ≥ JUNCTION_X → stop.
Phase 2 → Turn LEFT 90° using set_rotate (blocking, accurate).
Phase 3 → Line follower ON  → robot drives along the vertical road
           Watch odometer Y. When Y ≥ PARKING_Y → stop.
Phase 4 → Turn RIGHT 90° using set_rotate (blocking, accurate).
Phase 5 → Drive straight into parking bay using set_move_dist (blocking).

WHY NOT set_move_speed FOR MOVEMENT?
──────────────────────────────────────
set_move_speed is a continuous (non-blocking) command that needs to be
paired with a separate stop command. It has no built-in completion
feedback. For straight moves use set_move_dist (blocking).
For turns use set_rotate (blocking). These APIs wait until
the robot physically finishes before the script continues.

TUNE THESE VALUES before running
─────────────────────────────────
"""
import time
from DobotEDU import dobot_edu

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
PORT         = "COM4"    # USB COM port

TRACE_SPEED  = 20        # Line-following speed (5–50). 20 is safe.

# Odometer thresholds (cm) — adjust to match YOUR track dimensions
JUNCTION_X   = 85.0      # X cm at which the bottom road meets the junction
PARKING_Y    = 85.0      # Y cm at which to stop before the Small House slot

# Turn speed — set_rotate(angle_deg, speed_deg_per_s)
TURN_SPEED   = 40        # degrees per second for turns

# Parking final drive — set_move_dist(x_mm, y_mm, Vx, Vy)
PARK_DIST_MM = 300       # mm to drive into the parking bay (tune this)
PARK_SPEED   = 40        # mm/s for the parking drive

# Poll interval while waiting for odometer threshold
POLL_SEC     = 0.1
# ─────────────────────────────────────────────────────────────────────────────

print(f"Connecting to Magician GO on {PORT}...")
dobot_edu.set_portname(PORT)
go = dobot_edu.magiciango


# ── Helper functions ──────────────────────────────────────────────────────────

def start_trace(speed=TRACE_SPEED):
    """Start the built-in line follower."""
    go.set_running_mode(0)   # reset mode first — prevents robot staying still after set_rotate/set_move_dist
    time.sleep(0.2)
    go.set_trace_speed(speed)
    time.sleep(0.1)
    go.set_auto_trace(True)
    print(f"  [TRACE ON]  speed={speed}")

def stop_trace():
    """Stop the line follower safely (official two-step sequence)."""
    go.set_trace_speed(0)
    time.sleep(0.3)
    go.set_auto_trace(False)
    print("  [TRACE OFF]")

def turn_left(speed=TURN_SPEED):
    """Turn LEFT (CCW) 90° — blocking."""
    print(f"  [TURN LEFT] 90° at {speed} deg/s ...")
    go.set_rotate(90, speed)   # positive = CCW = left
    time.sleep(0.3)
    print("  [TURN LEFT] done")

def turn_right(speed=TURN_SPEED):
    """Turn RIGHT (CW) 90° — blocking."""
    print(f"  [TURN RIGHT] 90° at {speed} deg/s ...")
    go.set_rotate(-90, speed)  # negative = CW = right
    time.sleep(0.3)
    print("  [TURN RIGHT] done")

def read_pos():
    """Return (x, y, yaw) from the odometer."""
    p = go.get_odometer_data()
    return p['x'], p['y'], p['yaw']

def wait_for_x(threshold):
    """Line-follow while watching X. Stops and returns when X >= threshold."""
    print(f"  Waiting for X ≥ {threshold} cm ...")
    while True:
        x, y, yaw = read_pos()
        print(f"    X:{x:6.1f}  Y:{y:6.1f}  Yaw:{yaw:5.1f}°")
        if x >= threshold:
            print(f"  → X threshold reached: {x:.1f} cm")
            return x, y
        time.sleep(POLL_SEC)

def wait_for_y(threshold):
    """Line-follow while watching Y. Stops and returns when Y >= threshold."""
    print(f"  Waiting for Y ≥ {threshold} cm ...")
    while True:
        x, y, yaw = read_pos()
        print(f"    X:{x:6.1f}  Y:{y:6.1f}  Yaw:{yaw:5.1f}°")
        if y >= threshold:
            print(f"  → Y threshold reached: {y:.1f} cm")
            return x, y
        time.sleep(POLL_SEC)

def emergency_stop():
    """Best-effort full stop."""
    try:
        go.set_move_speed(0, 0, 0)
    except Exception:
        pass
    try:
        stop_trace()
    except Exception:
        pass


# ── Main navigation ───────────────────────────────────────────────────────────

try:
    # Verify connection
    battery = go.get_power_voltage()
    print(f"Connected!  Battery: {battery['powerPercentage']:.0f}%  ({battery['powerVoltage']:.2f} V)")

    # ── Reset odometer to (0, 0, 0) ──────────────────────────────────────────
    print("\nResetting odometer to (0, 0, 0) ...")
    go.set_odometer_data(0, 0, 0)
    time.sleep(0.5)
    x, y, yaw = read_pos()
    print(f"  Odometer: X={x:.1f}  Y={y:.1f}  Yaw={yaw:.1f}°")

    # ── PHASE 1: Line-follow along the BOTTOM ROAD ────────────────────────────
    print(f"\n{'='*55}")
    print(f"  PHASE 1: Bottom road → line-follow until X ≥ {JUNCTION_X} cm")
    print(f"  Place the robot ON the black line now!")
    print(f"{'='*55}")
    time.sleep(1.5)   # pause so you can read the message

    start_trace(TRACE_SPEED)
    wait_for_x(JUNCTION_X)
    stop_trace()
    time.sleep(0.5)

    # ── PHASE 2: Turn LEFT onto the VERTICAL ROAD ────────────────────────────
    print(f"\n{'='*55}")
    print("  PHASE 2: Turn LEFT 90°")
    print(f"{'='*55}")
    turn_left()

    # ── PHASE 3: Line-follow along the VERTICAL ROAD ─────────────────────────
    print(f"\n{'='*55}")
    print(f"  PHASE 3: Vertical road → line-follow until Y ≥ {PARKING_Y} cm")
    print(f"{'='*55}")
    start_trace(TRACE_SPEED)
    wait_for_y(PARKING_Y)
    stop_trace()
    time.sleep(0.5)

    # ── PHASE 4: Turn RIGHT to face the PARKING BAY ──────────────────────────
    print(f"\n{'='*55}")
    print("  PHASE 4: Turn RIGHT 90° to face parking bay")
    print(f"{'='*55}")
    turn_right()

    # ── PHASE 5: Drive straight INTO the parking bay ─────────────────────────
    print(f"\n{'='*55}")
    print(f"  PHASE 5: Drive {PARK_DIST_MM} mm into parking bay")
    print(f"{'='*55}")
    print(f"  Driving in at {PARK_SPEED} mm/s (blocking)...")
    go.set_move_dist(PARK_DIST_MM, 0, PARK_SPEED, 0)
    print("  Parking drive complete.")

    # ── SUCCESS ───────────────────────────────────────────────────────────────
    print("\n" + "[OK] " * 10)
    print("  Successfully parked at Small House!")
    print("[OK] " * 10)

    go.set_rgb_light("LED_ALL", 1, 0, 255, 0, 0, 0)   # Green LEDs
    go.set_buzzer_sound(1, 1000, 2)
    time.sleep(0.6)
    go.set_buzzer_sound(1, 1500, 2)
    time.sleep(0.6)
    go.set_buzzer_sound(1, 2000, 2)
    time.sleep(0.6)
    go.set_buzzer_sound(1, 0, 0)   # silence the buzzer

except KeyboardInterrupt:
    print("\n[WARN]  Interrupted – stopping.")
    emergency_stop()

except Exception as e:
    import traceback
    print("\n[ERROR]  Error – stopping.")
    emergency_stop()
    traceback.print_exc()
