import sys
import os
import time

sys.path.append(r"d:\DobotEDU")

# Monkey-Patch DobotRPC to bypass port 10001 connection hang
try:
    import DobotRPC.RPCClient
    import asyncio

    class MockWS:
        @property
        def open(self):
            return True
        async def send(self, *args, **kwargs):
            pass
        async def recv(self, *args, **kwargs):
            await asyncio.sleep(36000)

    original_init = DobotRPC.RPCClient.RPCClient.__init__
    original_wait = DobotRPC.RPCClient.RPCClient.wait_for_connected
    original_is_connected = DobotRPC.RPCClient.RPCClient.is_connected

    def patched_init(self, ip="localhost", port=9090, *args, **kwargs):
        if port == 10001:
            self._RPCClient__ip = ip
            self._RPCClient__port = port
            self._RPCClient__ws = MockWS()
            self._RPCClient__exchange_map = {}
            self._RPCClient__recv_task_timer = None
            self._RPCClient__client_name = "MockClient-10001"
            self._RPCClient__loop = asyncio.get_event_loop()
            return
        return original_init(self, ip, port, *args, **kwargs)

    async def patched_wait_for_connected(self):
        if self._RPCClient__port == 10001:
            return
        return await original_wait(self)

    @property
    def patched_is_connected(self):
        if self._RPCClient__port == 10001:
            return True
        return original_is_connected.fget(self)

    DobotRPC.RPCClient.RPCClient.__init__ = patched_init
    DobotRPC.RPCClient.RPCClient.wait_for_connected = patched_wait_for_connected
    DobotRPC.RPCClient.RPCClient.is_connected = patched_is_connected
except Exception as e:
    pass

from DobotEDU import dobot_edu
from magician_go_lite.core.lite_helper import safe_connect, safe_disconnect

PORT = "COM6"

def main():
    dobot_edu.set_portname(PORT)
    lite = dobot_edu.m_lite
    go = dobot_edu.magiciango
    beta_go = dobot_edu.beta_go

    print(f"Connecting to Magician Lite on {PORT} to establish serial session...")
    try:
        safe_connect(lite)
    except Exception as e:
        print(f"[ERROR] Could not connect to Magician Lite: {e}")
        return

    print("Checking connection to Magician GO...")
    try:
        battery = go.get_power_voltage()
        print(f"[OK] Battery: {battery.get('powerPercentage', 'N/A')}% ({battery.get('powerVoltage', 'N/A')} V)")
    except Exception as e:
        print(f"[ERROR] Could not query Magician GO: {e}")
        safe_disconnect(lite)
        return

    print("\nStarting stop sign detection patrol...")
    print("Place the robot on a line track. Put a STOP sign in front of the camera to stop it.")
    print("Press Ctrl+C to stop the script.")
    time.sleep(2.0)

    # State tracking to avoid spamming commands
    patrolling = None

    try:
        while True:
            # Query if STOP sign is detected
            stop_detected = beta_go.car_camera_is_detected(sign_name="stop")
            
            if stop_detected:
                print(f"[{time.strftime('%H:%M:%S')}] [DETECTION] STOP sign detected!")
                if patrolling is not False:
                    print("  -> Stopping patrol (speed=0, trace=0)")
                    go.set_trace_speed(speed=0)
                    time.sleep(0.1)
                    go.set_auto_trace(trace=0)
                    patrolling = False
            else:
                print(f"[{time.strftime('%H:%M:%S')}] [DETECTION] Clear (no STOP sign)")
                if patrolling is not True:
                    print("  -> Starting patrol (speed=20, trace=1)")
                    go.set_trace_speed(speed=20)
                    time.sleep(0.1)
                    go.set_auto_trace(trace=1)
                    patrolling = True
                    
            # 200ms sleep prevents port flooding
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\nStopping patrol safely...")
        try:
            go.set_trace_speed(speed=0)
            time.sleep(0.1)
            go.set_auto_trace(trace=0)
            print("[OK] Stopped.")
        except Exception as e:
            print(f"Failed to stop: {e}")
    finally:
        safe_disconnect(lite)

if __name__ == "__main__":
    main()
