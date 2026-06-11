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
    import argparse
    parser = argparse.ArgumentParser(description="Patrol and Log Signs")
    parser.add_argument("--speed", type=int, default=12, help="Patrol speed (default: 12)")
    parser.add_argument("--trace", type=int, default=2, help="Trace mode: 1 = Black line, 2 = White line (default: 2)")
    parser.add_argument("--p", type=int, default=None, help="Line tracking PID P-gain")
    parser.add_argument("--i", type=int, default=None, help="Line tracking PID I-gain")
    parser.add_argument("--d", type=int, default=None, help="Line tracking PID D-gain")
    args = parser.parse_args()

    speed = args.speed
    trace_mode = args.trace

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

    # Set custom PID if provided
    if args.p is not None or args.i is not None or args.d is not None:
        p_val = args.p if args.p is not None else 10
        i_val = args.i if args.i is not None else 0
        d_val = args.d if args.d is not None else 5
        print(f"Setting custom line tracking PID: P={p_val}, I={i_val}, D={d_val}...")
        try:
            go.set_trace_pid(p=p_val, i=i_val, d=d_val)
            print("[OK] PID parameters set successfully.")
        except Exception as e:
            print(f"[WARN] Failed to set PID: {e}")

    print(f"\nStarting Normal Line Tracking Patrol (Speed={speed}) and Logging Signs...")
    print("The robot will follow the line track continuously and print any signs it sees.")
    print("Press Ctrl+C to stop the robot and exit the script.")
    print("-" * 70)
    time.sleep(2.0)

    # Known sign mapping from DobotSDK
    all_signs = ["lors", "l", "p", "apt", "rors", "r", "stop", "spm", "t", "u", "wh", "z"]

    try:
        # Start automatic line patrol at the user-specified max speed
        go.set_trace_speed(speed=speed)
        time.sleep(0.1)
        go.set_auto_trace(trace=trace_mode)
        print(f"[STATUS] Line tracking patrol started (Max Speed={speed}, TraceMode={trace_mode})!")

        loop_counter = 0

        while True:
            # 1. Arm Keep-alive: only once every 1.2s (2 iterations)
            # This is frequent enough to prevent DobotLink timeout (< 2.5s) 
            # but slow enough to avoid any serial port congestion.
            if loop_counter % 2 == 0:
                try:
                    lite.get_pose()
                except Exception:
                    pass
            loop_counter += 1

            # 2. Read camera detections once every 600ms
            # At speed 12, the camera stays on the sign for ~1.5s, so 600ms is perfectly safe.
            camera_data = beta_go.get_car_camera_obj()
            count = camera_data.get('count', 0)
            objs = camera_data.get('dl_obj', [])
            
            if count > 0 or len(objs) > 0:
                detected = []
                for obj in objs:
                    _id = obj.get('id', -1)
                    name = all_signs[_id].upper() if (0 <= _id < len(all_signs)) else f"UNKNOWN_{_id}"
                    x = obj.get('x', 'N/A')
                    y = obj.get('y', 'N/A')
                    w = obj.get('w', 'N/A')
                    h = obj.get('h', 'N/A')
                    detected.append(f"{name} (id={_id}, size={w}x{h})")
                
                print(f"\n[{time.strftime('%H:%M:%S')}] DETECTED: {', '.join(detected)}")
            else:
                sys.stdout.write(".")
                sys.stdout.flush()
                
            # 600ms loop interval (1.6Hz) to completely eliminate serial port congestion
            time.sleep(0.6)

    except KeyboardInterrupt:
        print("\nStopping patrol safely...")
        try:
            go.set_trace_speed(speed=0)
            time.sleep(0.1)
            go.set_auto_trace(trace=0)
            print("[OK] Stopped.")
        except Exception as e:
            print(f"Failed to stop: {e}")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Script crashed: {e}")
        import traceback
        traceback.print_exc()
        try:
            print("Attempting to stop robot...")
            go.set_trace_speed(speed=0)
            time.sleep(0.1)
            go.set_auto_trace(trace=0)
            print("[OK] Stopped.")
        except Exception as stop_err:
            print(f"Failed to stop: {stop_err}")
    finally:
        safe_disconnect(lite)

if __name__ == "__main__":
    main()
