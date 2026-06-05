"""
lite_move.py
============
Shared movement helper for Magician Lite scripts.

Uses MOVJ_XYZ (joint interpolation) — same mode as homing:
  - Fast and smooth arc motion (no vibration)
  - No inverse kinematics mid-move = no micro-corrections
  - Much faster than MOVL_XYZ (linear Cartesian)

MOVL_XYZ is kept as an option for situations needing a straight line.
"""

import time
from pydobot.message import Message
from pydobot.enums import PTPMode

# Fixed sleep per move — covers any workspace move at the set speed
# At velocity=80 this is plenty of time. Reduce to 2.0 if moves feel done early.
MOVE_SLEEP   = 2.5
HOME_TIMEOUT = 5


def setup_speed(device, velocity=80, acceleration=40):
    """
    Set ALL PTP speed parameters for smooth motion.
    
    Key insight: keep velocity HIGH but acceleration LOW.
    Low acceleration = gentle ramp-up and ramp-down = no vibration.
    pydobot's speed() only sets common + coordinate params,
    missing joint params (which default to 200 — too aggressive).
    """
    # Common params (global ratio)
    device._set_ptp_common_params(velocity=velocity, acceleration=acceleration)
    # Cartesian coordinate params
    device._set_ptp_coordinate_params(velocity=velocity, acceleration=acceleration)
    # Per-joint params — 4 joints, velocity + acceleration each
    v = velocity * 2.5   # joint velocities in deg/s (scale up from ratio)
    a = acceleration * 2.5
    device._set_ptp_joint_params(v, v, v, v, a, a, a, a)


def move_to(device, x, y, z, r=0.0, linear=False):
    """
    Move using MOVJ_XYZ (joint interpolation) by default — fast and smooth.
    Set linear=True to use MOVL_XYZ for a straight-line Cartesian path.
    """
    mode = PTPMode.MOVL_XYZ if linear else PTPMode.MOVJ_XYZ
    device._set_ptp_cmd(x, y, z, r, mode=mode, wait=False)
    time.sleep(MOVE_SLEEP)


def send_home(device, timeout=HOME_TIMEOUT):
    """Send home command and wait for completion."""
    msg = Message()
    msg.id    = 31
    msg.ctrl  = 0x03
    msg.params = bytearray([])
    device._send_command(msg, wait=False)
    print(f"  Homing — waiting {timeout}s ...")
    time.sleep(timeout)
    device.ser.reset_input_buffer()


def suction_on(device, delay=0.8):
    """Enable end effector AND start pump: [0x01, 0x01]"""
    msg = Message()
    msg.id     = 62
    msg.ctrl   = 0x03
    msg.params = bytearray([0x01, 0x01])
    device._send_command(msg)
    time.sleep(delay)


def suction_off(device, delay=0.8):
    """Disable end effector AND stop pump completely: [0x00, 0x00]"""
    msg = Message()
    msg.id     = 62
    msg.ctrl   = 0x03
    msg.params = bytearray([0x00, 0x00])
    device._send_command(msg)
    time.sleep(0.3)
    device._send_command(msg)   # send twice to be sure
    time.sleep(delay)


def gripper_open(device, delay=0.6):
    device.grip(False)
    time.sleep(delay)


def gripper_close(device, delay=0.6):
    device.grip(True)
    time.sleep(delay)
