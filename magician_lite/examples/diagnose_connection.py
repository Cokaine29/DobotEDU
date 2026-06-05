"""
diagnose_connection.py
======================
Diagnoses the DobotLink connection state and tries to force-disconnect
any stale Magician Lite session using raw RPC calls.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import time
import asyncio
from DobotRPC import RPCClient

PORT = "COM8"

loop = asyncio.get_event_loop()
client = RPCClient(loop=loop)

print("Waiting for WebSocket connection to DobotLink...")
time.sleep(2)

if not client.is_connected:
    print("[FAIL] Cannot reach DobotLink on ws://localhost:9090")
    print("       >> Make sure DobotLink desktop app is RUNNING")
else:
    print("[OK] Connected to DobotLink WebSocket\n")

    # Try to force-disconnect the Lite from DobotLink side
    print(f"Sending DisconnectDobot to MagicianLite on {PORT} ...")
    try:
        result = loop.run_until_complete(
            client.send("MagicianLite.DisconnectDobot", {
                "portName": PORT,
                "queueStop": True,
                "queueClear": True,
                "isQueued": False
            })
        )
        print(f"  DisconnectDobot result: {result}")
    except Exception as e:
        print(f"  DisconnectDobot error (expected if nothing was open): {e}")

    time.sleep(1.5)

    # Now try to connect fresh
    print(f"\nSending ConnectDobot to MagicianLite on {PORT} ...")
    try:
        result = loop.run_until_complete(
            client.send("MagicianLite.ConnectDobot", {
                "portName": PORT,
                "queueStart": True,
                "isQueued": False
            })
        )
        print(f"  [OK] ConnectDobot result: {result}")

        # Immediately disconnect cleanly
        time.sleep(0.5)
        loop.run_until_complete(
            client.send("MagicianLite.DisconnectDobot", {
                "portName": PORT,
                "queueStop": True,
                "queueClear": True,
                "isQueued": False
            })
        )
        print("  [OK] Disconnected cleanly.\n")
        print("[SUCCESS] DobotLink can connect to the Magician Lite!")
        print("          You can now run 01_connect_and_home.py normally.")

    except Exception as e:
        print(f"\n[FAIL] ConnectDobot failed: {e}")
        print("\nPossible causes:")
        print("  1. Wrong COM port — check Device Manager for the correct COMx")
        print("  2. Robot is not powered on")
        print("  3. USB cable is not properly connected")
        print("  4. Another app (DobotStudio, etc.) has the port open")
        print("  5. DobotLink needs to be restarted")
