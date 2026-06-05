"""
lite_helper.py
==============
Core helper functions for Dobot Magician Lite using the DobotEDU library.
"""

import time
from DobotEDU import dobot_edu

def get_lite(port: str):
    """Set the port and return the m_lite object."""
    dobot_edu.set_portname(port)
    return dobot_edu.m_lite

def safe_connect(lite, retries: int = 3, delay: float = 1.5):
    """Disconnect any stale session, then connect fresh."""
    print("  Releasing any stale DobotLink session ...")
    try:
        lite.disconnect_dobot()
        time.sleep(delay)
    except Exception:
        pass

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            lite.connect_dobot()
            print(f"  [OK] Connected! (attempt {attempt})")
            return
        except Exception as e:
            last_err = e
            print(f"  [WARN] Connect attempt {attempt} failed: {e}")
            if attempt < retries:
                print(f"  Retrying in {delay}s ...")
                try:
                    lite.disconnect_dobot()
                except Exception:
                    pass
                time.sleep(delay)

    raise RuntimeError(f"Could not connect to Dobot Lite on {lite.get_portname()}: {last_err}")

def safe_disconnect(lite):
    """Disconnect cleanly, suppressing errors."""
    try:
        lite.disconnect_dobot()
        print("  [OK] Disconnected cleanly.")
    except Exception:
        pass

def move_to(lite, x, y, z, r=0.0, ptp_mode=1, delay=2.5):
    """
    Move the Magician Lite arm to (X, Y, Z, R).
    ptp_mode: 1 = MOVJ_XYZ (joint interpolation, smooth), 2 = MOVL_XYZ (linear)
    """
    lite.set_ptpcmd(ptp_mode=ptp_mode, x=x, y=y, z=z, r=r)
    time.sleep(delay)

def suction_on(lite, delay=0.8):
    """Enable suction cup and turn on pump."""
    lite.set_endeffector_suctioncup(enable=True, on=True)
    time.sleep(delay)

def suction_off(lite, delay=0.8):
    """Disable suction cup and turn off pump."""
    lite.set_endeffector_suctioncup(enable=True, on=False)
    time.sleep(delay)

def gripper_close(lite, delay=0.6):
    """Close the gripper."""
    lite.set_endeffector_gripper(enable=True, on=True)
    time.sleep(delay)

def gripper_open(lite, delay=0.6):
    """Open the gripper."""
    lite.set_endeffector_gripper(enable=True, on=False)
    time.sleep(delay)

def read_stable_pose(lite, retries=5):
    """Reads current robot pose stably."""
    for attempt in range(retries):
        time.sleep(0.2)
        pose_data = lite.get_pose()
        if pose_data:
            x = pose_data.get('x', 9999)
            y = pose_data.get('y', 9999)
            z = pose_data.get('z', 9999)
            r = pose_data.get('r', 0)
            if abs(x) < 1000 and abs(y) < 1000 and abs(z) < 1000:
                return [x, y, z, r]
    return None
