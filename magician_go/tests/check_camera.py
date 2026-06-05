import time
from DobotEDU import dobot_edu

port = "COM4"
print(f"Connecting to Magician GO on {port}...")
dobot_edu.set_portname(port)
go = dobot_edu.magiciango

try:
    print("Reading camera and line-tracking data...")
    for i in range(10):
        # Read the line angle detected by the chassis camera
        trace_data = go.get_trace_angle()
        # Read objects detected by the chassis camera
        camera_objs = go.get_car_camera_obj()
        
        print(f"[{i}] Trace Line Angle: {trace_data.get('angle', 'N/A')} degrees")
        print(f"[{i}] Detected Objects Count: {camera_objs.get('count', 'N/A')}")
        if camera_objs.get('count', 0) > 0:
            print(f"    Objects: {camera_objs.get('dl_obj')}")
            
        time.sleep(0.5)

except Exception as e:
    import traceback
    traceback.print_exc()
