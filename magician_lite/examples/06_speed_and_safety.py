"""
06_speed_and_safety.py
======================
Demonstrates:
  - Setting PTP speed ratios
  - Setting arm speed ratios
  - Enabling collision detection
  - Reading and clearing alarms
  - Lost-step detection

Use this script as a reference for safe, production-style robot control.

Requirements:
  - DobotLink must be running
  - Adjust PORT as needed
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from core.lite_helper import get_lite, safe_connect, safe_disconnect

# ── Configuration ─────────────────────────────────────────────────────────────
PORT = "COM8"

lite = get_lite(PORT)

try:
    safe_connect(lite)
    print()

    # ── 1. PTP speed control ───────────────────────────────────────────────────
    print("[1] Setting PTP speed ratios ...")

    # Global PTP speed (velocity % and acceleration %)
    lite.set_ptpcommon_params(velocity_ratio=30, acceleration_ratio=30)
    params = lite.get_ptpcommon_params()
    print(f"    PTP Common Params: {params}")

    # Per-axis PTP joint speed (lists of 4 values, one per joint)
    lite.set_ptpjoint_param(
        velocity=[100, 100, 100, 100],
        acceleration=[80, 80, 80, 80]
    )
    joint_params = lite.get_ptpjoint_param()
    print(f"    PTP Joint Params:  {joint_params}")

    # Cartesian PTP speed
    lite.set_ptpcoordinate_params(
        xyz_velocity=100.0, r_velocity=100.0,
        xyz_acceleration=80.0, r_acceleration=80.0
    )
    coord_params = lite.get_ptpcoordinate_params()
    print(f"    PTP Coord Params:  {coord_params}\n")

    # ── 2. Arm speed ratio ─────────────────────────────────────────────────────
    print("[2] Setting arm speed ratio ...")
    # type 0 = velocity, type 1 = acceleration
    lite.set_armspeed_ratio(set_type=0, set_value=50)
    lite.set_armspeed_ratio(set_type=1, set_value=50)

    vel = lite.get_armspeed_ratio(get_type=0)
    acc = lite.get_armspeed_ratio(get_type=1)
    print(f"    Velocity ratio: {vel}")
    print(f"    Accel ratio:    {acc}\n")

    # ── 3. Collision detection ─────────────────────────────────────────────────
    print("[3] Enabling collision detection ...")
    lite.set_collision_check(enable=True, thre_shold=0.5)
    state = lite.get_collision_check()
    print(f"    Collision check state: {state}\n")

    # ── 4. Lost-step detection ─────────────────────────────────────────────────
    print("[4] Setting lost-step threshold ...")
    lite.set_lost_step_params(value=0.5)
    lite.set_lost_step_cmd()
    result = lite.get_lost_step_result()
    print(f"    Lost-step result: {result}\n")

    # ── 5. Alarms ─────────────────────────────────────────────────────────────
    print("[5] Reading alarms ...")
    alarms = lite.get_alarms_state()
    print(f"    Alarms: {alarms}")

    print("    Clearing all alarms ...")
    lite.clean_alarm()
    print("    Alarms cleared.\n")

    # ── 6. JUMP params (safe arc over obstacles) ───────────────────────────────
    print("[6] Setting JUMP params ...")
    lite.set_ptpjump_params(z_limit=120.0, jump_height=40.0)
    jump_params = lite.get_ptpjump_params()
    print(f"    JUMP params: {jump_params}\n")

    # ── 7. Demonstrate a slow, safe move ──────────────────────────────────────
    print("[7] Performing a slow test move ...")
    lite.set_ptpcommon_params(velocity_ratio=20, acceleration_ratio=20)
    lite.set_ptpcmd(ptp_mode=1, x=200.0, y=0.0, z=60.0, r=0.0)
    pose = lite.get_pose()
    print(f"    Arrived at: X={pose['x']} Y={pose['y']} Z={pose['z']}")

    print("\n[DONE]")

except Exception as e:
    import traceback
    print("\n[ERROR]")
    traceback.print_exc()

finally:
    safe_disconnect(lite)
