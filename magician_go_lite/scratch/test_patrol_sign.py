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

    print("\nStarting stop sign detection patrol (with 1.0s debouncing)...")
    print("Place the robot on a line track. Put a STOP sign in front of the camera to stop it.")
    print("Press Ctrl+C to stop the script.")
    time.sleep(2.0)

    # State tracking to avoid command spamming
    patrolling = None
    
    # Debouncing tracking for resuming patrol
    clear_counter = 0
    CLEAR_THRESHOLD = 5 # Needs 5 consecutive clear frames (approx 1.0s) to resume patrol
    
    # Sign names mapping
    all_signs = ["lors", "l", "p", "apt", "rors", "r", "stop", "spm", "t", "u", "wh", "z"]

    try:
        while True:
            # Read raw camera objects list
            camera_data = beta_go.get_car_camera_obj()
            count = camera_data.get('count', 0)
            
            # Find if STOP sign is in detected list
            stop_detected = False
            detected_signs = []
            
            if count > 0:
                for obj in camera_data.get('dl_obj', []):
                    _id = obj.get('id', -1)
                    if 0 <= _id < len(all_signs):
                        sign_name = all_signs[_id]
                        detected_signs.append(sign_name.upper())
                        if sign_name == "stop":
                            stop_detected = True
            
            # Query ultrasonic front distance to handle close-up occlusion/losing target
            try:
                dist_data = go.get_ultrasonic_data()
                front_dist = dist_data.get('front', 40.0)
            except Exception as e:
                front_dist = 40.0
                
            if stop_detected:
                print(f"[{time.strftime('%H:%M:%S')}] [DETECTION] STOP sign detected! (Detected: {detected_signs}, Front: {front_dist:.1f} cm)")
                clear_counter = 0 # Reset clear frame counter immediately
                if patrolling is not False:
                    print("  -> Stopping patrol (speed=0, trace=0)")
                    go.set_trace_speed(speed=0)
                    time.sleep(0.1)
                    go.set_auto_trace(trace=0)
                    patrolling = False
            else:
                # If we are stopped, safeguard against resuming if the sign is still physically close but camera lost it
                is_blocked = False
                if patrolling is False:
                    if front_dist < 35.0:
                        is_blocked = True
                        print(f"[{time.strftime('%H:%M:%S')}] [DETECTION] STOP sign not seen, but front obstacle detected at {front_dist:.1f} cm. Remaining stopped.")
                        clear_counter = 0 # Keep clear counter reset
                
                if not is_blocked:
                    clear_counter += 1
                    if count > 0:
                        print(f"[{time.strftime('%H:%M:%S')}] [DETECTION] Clear (Other signs: {detected_signs}, Front: {front_dist:.1f} cm) (Clear frames: {clear_counter}/{CLEAR_THRESHOLD})")
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] [DETECTION] Clear (no signs, Front: {front_dist:.1f} cm) (Clear frames: {clear_counter}/{CLEAR_THRESHOLD})")
                    
                    # Resume patrol ONLY if path has been clear for CLEAR_THRESHOLD consecutive frames
                    if clear_counter >= CLEAR_THRESHOLD:
                        if patrolling is not True:
                            print("  -> Starting patrol (speed=20, trace=1)")
                            go.set_trace_speed(speed=20)
                            time.sleep(0.1)
                            go.set_auto_trace(trace=1)
                            patrolling = True
            
            # 200ms polling rate
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
