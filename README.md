# Dobot Robotics Workspace (GO & Lite)

An organized, publication-ready repository containing control and computer vision scripts for educational robotics:
1. **Dobot Magician GO**: A mobile chassis with built-in line-tracking sensor and navigation algorithms.
2. **Dobot Magician Lite**: A 4-axis robotic arm with suction cup/gripper end-effectors and advanced vision-guided capabilities.

---

## Directory Layout

```
DobotEDU/
  ├── dependencies/                      # Local wheels/packages
  │     └── dobotedu-2.2.2-py3-none-any.whl
  ├── requirements.txt                  # Python dependencies list
  ├── README.md                         # Main documentation
  │
  ├── magician_go/                      # Magician GO Mobile Robot Chassis
  │     ├── navigation/                 # Line-following, tracking, and parking
  │     │     ├── navigate_to_small_house.py
  │     │     ├── lane_keeper_navigation.py
  │     │     └── trace_line.py
  │     └── tests/                      # Basic hardware checks (rotate, speed, buzzer)
  │           ├── check_camera.py
  │           ├── test_direct_rpc.py
  │           └── test_magiciango.py
  │
  └── magician_lite/                    # Magician Lite Robotic Arm
        ├── core/                       # Shared hardware connection & control helpers
        │     ├── lite_move.py          # Fast MOVJ moves, suction commands, speed setup
        │     └── lite_helper.py        # Connection adapter for stale DobotLink sessions
        ├── config/                     # Calibration and taught target files (git-ignored)
        │     ├── calibration.json      # Affine mapping matrix
        │     └── drop_targets.json     # Custom color-to-drop coordinates
        ├── examples/                   # Baseline tests, gripper control, and shapes
        │     ├── 00_read_pose.py       # Cartesian & Joint coordinate reader
        │     ├── 03_suction_cup_pick_place.py
        │     ├── 04_gripper_pick_place.py
        │     └── pick_and_place.py     # High-speed smooth baseline pick-and-place
        └── vision/                     # Smart Computer Vision Application
              ├── vision_pick_place.py  # Main vision loop with ROI filters, sorting, and stacking
              ├── calibration.py        # 3-point interactive pixel-to-robot calibration
              └── teach_drop_targets.py # Manual target-teaching walkthrough tool
```

---

## Installation & Setup

1. **Clone/Open Workspace**:
   Navigate to the directory `d:\DobotEDU`.

2. **Initialize Virtual Environment**:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install Core Requirements**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Install DobotEDU Desktop Library**:
   ```powershell
   pip install dependencies/dobotedu-2.2.2-py3-none-any.whl
   ```

---

## Running Scripts

*Ensure DobotLab is closed before running any python scripts to avoid COM port locking conflicts.*

### Magician GO (Mobile Chassis)
Run navigation scripts:
```powershell
.venv\Scripts\python.exe magician_go/navigation/navigate_to_small_house.py
```

---

### Magician Lite (Robotic Arm)

#### 1. Connection & Coordinate Check
Perform a basic connection test and print coordinates:
```powershell
.venv\Scripts\python.exe magician_lite/examples/00_read_pose.py
```

#### 2. Coordinate Calibration (Camera to Robot)
Map the camera pixels to the robot's coordinate system using an interactive 3-point routine:
```powershell
.venv\Scripts\python.exe magician_lite/vision/calibration.py
```

#### 3. Teach Drop Targets (Bins)
Unlock the motors and manually place the arm at your custom bins to save target coordinates for Red, Yellow, Blue, Green:
```powershell
.venv\Scripts\python.exe magician_lite/vision/teach_drop_targets.py
```

#### 4. Run AI Vision Sorting/Stacking
Automatically detect and sort/stack all blocks in one go using the vision system:
```powershell
# Standard color sorting (using suction cup)
.venv\Scripts\python.exe magician_lite/vision/vision_pick_place.py

# Stacking mode (using suction cup)
.venv\Scripts\python.exe magician_lite/vision/vision_pick_place.py --stack

# Run with Gripper end-effector (automatically uses Z=10.0 and rotates wrist claws to align)
.venv\Scripts\python.exe magician_lite/vision/vision_pick_place.py --gripper

# Run with Gripper in Stacking mode
.venv\Scripts\python.exe magician_lite/vision/vision_pick_place.py --gripper --stack

# Customize the Z pick height (e.g. set pick Z to 12.5mm)
.venv\Scripts\python.exe magician_lite/vision/vision_pick_place.py --gripper --pick-z 12.5

# Run a live video preview of block detection and orientation angles on screen
.venv\Scripts\python.exe magician_lite/vision/vision_pick_place.py --preview
```
