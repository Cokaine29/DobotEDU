"""
lite_helper.py
==============
Shared helper for all Magician Lite scripts.

Provides `safe_connect()` which:
  1. Tries to disconnect any stale DobotLink session (fixes error code 6)
  2. Waits briefly for DobotLink to release the port
  3. Connects fresh

Error code 6 meaning:
  DobotLink internally still has the COM port "open" from a previous
  Python session that crashed without calling disconnect_dobot().
  The only reliable fix is to force-disconnect inside DobotLink first.
"""

import time
from DobotEDU import dobot_edu


def get_lite(port: str):
    """Set the port and return the m_lite object."""
    dobot_edu.set_portname(port)
    return dobot_edu.m_lite


def safe_connect(lite, retries: int = 3, delay: float = 1.5):
    """
    Disconnect any stale DobotLink session, then connect fresh.
    Retries `retries` times with `delay` seconds between attempts.

    Fixes:
      NetworkError code 6 — 'An error occurred while attempting to
      open an already opened device in this object.'
    """
    # Step 1: force-disconnect through DobotLink (clears its internal state)
    print("  Releasing any stale DobotLink session ...")
    try:
        lite.disconnect_dobot()
        time.sleep(delay)   # give DobotLink time to fully release the port
        print("  [OK] Stale session released.")
    except Exception:
        pass  # nothing was open — that's fine

    # Step 2: attempt to connect, with retries
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            lite.connect_dobot()
            print(f"[OK] Connected! (attempt {attempt})")
            return   # success
        except Exception as e:
            last_err = e
            err_str = str(e)
            print(f"  [WARN] Connect attempt {attempt} failed: {err_str}")
            if attempt < retries:
                print(f"  Retrying in {delay}s ...")
                # Try disconnecting again before the next attempt
                try:
                    lite.disconnect_dobot()
                except Exception:
                    pass
                time.sleep(delay)

    # All retries exhausted
    raise RuntimeError(
        f"Could not connect after {retries} attempts.\n"
        "Please try:\n"
        "  1. Restart DobotLink desktop app\n"
        "  2. Unplug and replug the USB cable\n"
        "  3. Check the COM port number is correct\n"
        f"Last error: {last_err}"
    )


def safe_disconnect(lite):
    """Disconnect cleanly, suppressing errors if already disconnected."""
    try:
        lite.disconnect_dobot()
        print("Disconnected.")
    except Exception:
        pass
