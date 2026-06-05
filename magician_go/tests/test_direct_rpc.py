import time
from DobotEDU import dobot_edu

port = "COM4"
print(f"Connecting to Magician GO on {port}...")
dobot_edu.set_portname(port)

# Access the direct RPC adapter
adapter = dobot_edu._adapter

try:
    print("Testing direct RPC SetRotate (90 degrees, speed 40)...")
    # Call SetRotate directly with isQueued=False and isWaitForFinish=False to prevent hanging
    adapter.MagicianGO.SetRotate(
        portName=port,
        r=90,
        Vr=40,
        isQueued=False,
        isWaitForFinish=False
    )
    print("Command sent. Waiting 3 seconds for rotation...")
    time.sleep(3)
    
    print("Testing direct RPC SetMoveDist (move 150mm forward, speed 50)...")
    # Call SetMoveDist directly with isQueued=False and isWaitForFinish=False
    adapter.MagicianGO.SetMoveDist(
        portName=port,
        x=150,
        y=0,
        Vx=50,
        Vy=0,
        isQueued=False,
        isWaitForFinish=False
    )
    print("Command sent. Waiting 4 seconds for movement...")
    time.sleep(4)
    print("Test complete.")

except Exception as e:
    import traceback
    traceback.print_exc()
