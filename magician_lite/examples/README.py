"""
README — Dobot Magician Lite Scripts
=====================================

Folder: magician_lite/

Prerequisites
-------------
1. DobotLink desktop application must be RUNNING before any script.
2. Connect the Magician Lite via USB.
3. Set PORT = "COMx" in each script to match your actual serial port.
   (Check Device Manager → Ports to find the correct COM port.)
4. Activate the virtual environment before running:

   cd d:\DobotEDU
   .venv\Scripts\activate
   python magician_lite\<script>.py

Scripts Overview
----------------

| File                          | Description                                    |
|-------------------------------|------------------------------------------------|
| 01_connect_and_home.py        | Connect, read device info, home the robot      |
| 02_move_ptp.py                | Point-to-Point movement, waypoints, JUMP mode  |
| 03_suction_cup_pick_place.py  | Pick and place using suction cup               |
| 04_gripper_pick_place.py      | Pick and place using gripper                   |
| 05_draw_shapes.py             | Draw square / triangle / circle with CP motion |
| 06_speed_and_safety.py        | Speed ratios, collision detect, alarm handling |
| 07_sorting_demo.py            | Multi-slot sorting demo (suction cup)          |

Quick Reference — Key API Calls
---------------------------------

  from DobotEDU import dobot_edu
  dobot_edu.set_portname("COM4")
  lite = dobot_edu.m_lite          # ← always use m_lite for Magician Lite

  lite.connect_dobot()             # connect
  lite.set_homecmd()               # home
  lite.get_pose()                  # read current X/Y/Z/R and joint angles
  lite.set_ptpcmd(mode, x,y,z,r)  # PTP move  (mode 1 = MOVJ, 2 = MOVL)
  lite.set_ptpcommon_params(v, a)  # set speed ratio (0-100)
  lite.set_cpcmd(mode, x,y,z, pw) # Continuous Path move
  lite.set_endeffector_suctioncup(enable, on)  # suction cup
  lite.set_endeffector_gripper(enable, on)     # gripper
  lite.get_alarms_state()          # read alarms
  lite.clean_alarm()               # clear alarms
  lite.disconnect_dobot()          # disconnect

PTP Modes
----------
  0 = JUMP_XYZ     (lift over obstacles, go to XYZ)
  1 = MOVJ_XYZ     (joint interpolation, fastest)
  2 = MOVL_XYZ     (linear / straight-line Cartesian)
  6 = MOVL_INC     (relative linear move)
  7 = MOVJ_INC     (relative joint move)

Coordinate System
-----------------
  - X, Y, Z in millimetres (mm)
  - R (end-effector rotation) in degrees
  - Origin is the robot base centre
  - Positive X = forward  |  Positive Y = left  |  Positive Z = up

Safety Tips
-----------
  * Always home before running movement scripts.
  * Keep Z_HOVER (travel height) well above any objects on the table.
  * Use try/finally to ensure disconnect_dobot() is always called.
  * Turn off suction / open gripper in the except block as a safety measure.
  * Start with low speed ratios (20-30%) when testing new positions.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# This file is documentation only — not meant to be executed directly.
