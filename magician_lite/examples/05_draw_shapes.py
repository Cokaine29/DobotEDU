"""
05_draw_shapes.py
=================
Draws a square, triangle, and circle using pydobot.
Attach a pen/marker end-effector. Set Z_DRAW to the height
where the pen just touches the surface.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import math
from pydobot import Dobot
from core.lite_move import move_to, send_home

PORT    = "COM8"
Z_DRAW  = 0.0    # Z when pen touches surface (tune this!)
Z_HOVER = 60.0   # Z for travel
CX, CY  = 200.0, 0.0  # workspace centre

def draw_square(device, cx, cy, side=50.0):
    print(f"  Square: centre=({cx},{cy}) side={side}mm")
    h = side / 2
    corners = [(cx-h,cy-h),(cx+h,cy-h),(cx+h,cy+h),(cx-h,cy+h),(cx-h,cy-h)]
    move_to(device, corners[0][0], corners[0][1], Z_HOVER)
    move_to(device, corners[0][0], corners[0][1], Z_DRAW)
    for x, y in corners[1:]:
        move_to(device, x, y, Z_DRAW)
    move_to(device, corners[0][0], corners[0][1], Z_HOVER)

def draw_triangle(device, cx, cy, side=55.0):
    print(f"  Triangle: centre=({cx},{cy}) side={side}mm")
    h = (math.sqrt(3)/2) * side
    verts = [(cx, cy+2*h/3),(cx+side/2, cy-h/3),(cx-side/2, cy-h/3),(cx, cy+2*h/3)]
    move_to(device, verts[0][0], verts[0][1], Z_HOVER)
    move_to(device, verts[0][0], verts[0][1], Z_DRAW)
    for x, y in verts[1:]:
        move_to(device, x, y, Z_DRAW)
    move_to(device, verts[0][0], verts[0][1], Z_HOVER)

def draw_circle(device, cx, cy, radius=30.0, segments=18):
    print(f"  Circle: centre=({cx},{cy}) r={radius}mm")
    move_to(device, cx+radius, cy, Z_HOVER)
    move_to(device, cx+radius, cy, Z_DRAW)
    for i in range(1, segments+1):
        a = 2*math.pi*i/segments
        move_to(device, cx+radius*math.cos(a), cy+radius*math.sin(a), Z_DRAW)
    move_to(device, cx+radius, cy, Z_HOVER)

print(f"Connecting on {PORT} ...")
try:
    device = Dobot(port=PORT, verbose=False)
    print("[OK] Connected!\n")
    device.speed(velocity=40, acceleration=40)

    print("Homing ..."); send_home(device); print("[OK] Home done\n")

    print("Drawing shapes ...\n")
    draw_square(device,   CX, CY - 80, side=50)
    draw_triangle(device, CX, CY,      side=55)
    draw_circle(device,   CX, CY + 85, radius=30)

    move_to(device, 200.0, 0.0, Z_HOVER)
    print("\n[DONE] All shapes drawn!")

except Exception as e:
    import traceback
    print("\n[ERROR]"); traceback.print_exc()

finally:
    try: device.close(); print("Disconnected.")
    except Exception: pass
