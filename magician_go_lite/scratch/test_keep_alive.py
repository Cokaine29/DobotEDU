import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
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

from core.lite_helper import get_lite, safe_connect, safe_disconnect
from DobotEDU import dobot_edu

PORT = "COM6"

def keep_alive_sleep(lite, duration, interval=0.2):
    print(f"  Sleeping for {duration}s with keep-alive...")
    start_time = time.time()
    while time.time() - start_time < duration:
        try:
            lite.get_pose()
        except Exception as e:
            print(f"    [WARN] Pose keep-alive failed: {e}")
        time_to_sleep = min(interval, duration - (time.time() - start_time))
        if time_to_sleep > 0:
            time.sleep(time_to_sleep)

def test_run():
    dobot_edu.set_portname(PORT)
    lite = get_lite(PORT)
    try:
        safe_connect(lite)
        
        # Test Move 1
        print("\n--- Moving to X=200, Y=0, Z=50 ---")
        lite.set_ptpcmd(ptp_mode=1, x=200.0, y=0.0, z=50.0, r=0.0)
        keep_alive_sleep(lite, 3.0)
        
        # Test Move 2
        print("\n--- Moving to X=240, Y=0, Z=50 ---")
        lite.set_ptpcmd(ptp_mode=1, x=240.0, y=0.0, z=50.0, r=0.0)
        keep_alive_sleep(lite, 3.0)
        
        print("\n--- Move test complete! ---")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        safe_disconnect(lite)

if __name__ == "__main__":
    test_run()
