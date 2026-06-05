"""
lane_keeper_navigation.py
=========================
(This was a PID-based lane-keeping experiment that did NOT work
because set_move_speed does not reliably move the robot on its own,
and the odometer stayed at 0,0 because the robot never moved.)

REPLACED WITH: A clean line-follower + odometer approach identical
to navigate_to_small_house.py. Please use navigate_to_small_house.py
for the actual run.

This file is kept as a reference / explanation of what went wrong.

─────────────────────────────────────────────────────────────────────
WHAT WENT WRONG IN THE ORIGINAL VERSION
─────────────────────────────────────────────────────────────────────
The original script used:
    go.set_move_speed(base_speed, 0, steer_speed)  ← continuous command

And then polled the odometer in a while loop expecting X / Y to grow.

But the odometer reports 0, 0, 0 when:
  a) set_move_speed was issued but the robot firmware ignores it
     (e.g. it's in line-trace mode from a previous DobotLab session), OR
  b) The robot wheels are not touching the ground / slipping.

The fix: use set_auto_trace (confirmed to work) as the movement engine,
and set_rotate / set_move_dist (both blocking) for turns and parking.
─────────────────────────────────────────────────────────────────────
"""

# ── Re-export: just run navigate_to_small_house.py instead ────────────────────
print("This file has been replaced.")
print("Please run: navigate_to_small_house.py")
print()
print("  .venv\\Scripts\\python navigate_to_small_house.py")
