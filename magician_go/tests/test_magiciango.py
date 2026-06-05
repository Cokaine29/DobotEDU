"""
test_magiciango.py
==================
Basic connection and sensor test for the Dobot Magician GO.
Tests: battery, LEDs, buzzer, and ultrasonic sensors.

BUG FIXED: set_rgb_light needs 7 args after port injection:
  go.set_rgb_light(number, effect, r, g, b, cycle, counts)
"""
import time
from DobotEDU import dobot_edu

PORT = "COM4"

print(f"Connecting to Magician GO on {PORT}...")
dobot_edu.set_portname(PORT)
go = dobot_edu.magiciango

try:
    # ── 1. Battery status ─────────────────────────────────────────────────────
    print("\n[1] Reading battery...")
    battery = go.get_power_voltage()
    print(f"    [OK] Connected!")
    print(f"    Battery Voltage:    {battery.get('powerVoltage', 'N/A')} V")
    print(f"    Battery Percentage: {battery.get('powerPercentage', 'N/A')} %")

    # ── 2. RGB LEDs ───────────────────────────────────────────────────────────
    # Signature (after port injection):
    #   set_rgb_light(number, effect, r, g, b, cycle, counts)
    #   number : "LED_1"/"LED_2"/"LED_3"/"LED_4"/"LED_ALL"
    #   effect : 1 = solid, 2 = blink, 3 = fade
    #   r,g,b  : 0-255
    #   cycle  : 0
    #   counts : 0
    print("\n[2] Flashing LEDs...")
    print("    GREEN")
    go.set_rgb_light("LED_ALL", 1, 0, 255, 0, 0, 0)
    time.sleep(0.8)

    print("    BLUE")
    go.set_rgb_light("LED_ALL", 1, 0, 0, 255, 0, 0)
    time.sleep(0.8)

    print("    RED")
    go.set_rgb_light("LED_ALL", 1, 255, 0, 0, 0, 0)
    time.sleep(0.8)

    print("    OFF")
    go.set_rgb_light("LED_ALL", 1, 0, 0, 0, 0, 0)
    time.sleep(0.3)

    # ── 3. Buzzer ─────────────────────────────────────────────────────────────
    # Signature (after port injection):
    #   set_buzzer_sound(index, tone, beat)
    #   index : 1
    #   tone  : frequency in Hz  (0 = silence/off)
    #   beat  : duration in beats
    # IMPORTANT: Always send tone=0, beat=0 at the end to silence the buzzer!
    print("\n[3] Playing chime...")
    go.set_buzzer_sound(1, 800, 1)
    time.sleep(0.5)
    go.set_buzzer_sound(1, 1200, 1)
    time.sleep(0.5)
    go.set_buzzer_sound(1, 1600, 1)
    time.sleep(0.5)
    go.set_buzzer_sound(1, 0, 0)   # silence the buzzer
    time.sleep(0.2)

    # ── 4. Ultrasonic sensors ─────────────────────────────────────────────────
    print("\n[4] Reading ultrasonic sensors...")
    dist = go.get_ultrasonic_data()
    print(f"    Front: {dist.get('front', 'N/A')} cm")
    print(f"    Back:  {dist.get('back',  'N/A')} cm")
    print(f"    Left:  {dist.get('left',  'N/A')} cm")
    print(f"    Right: {dist.get('right', 'N/A')} cm")

    # ── 5. Odometer ───────────────────────────────────────────────────────────
    print("\n[5] Reading odometer...")
    pos = go.get_odometer_data()
    print(f"    X:   {pos.get('x',   'N/A')} cm")
    print(f"    Y:   {pos.get('y',   'N/A')} cm")
    print(f"    Yaw: {pos.get('yaw', 'N/A')} °")

    print("\n[DONE] All tests passed!")

except Exception as e:
    import traceback
    print("\n[ERROR] Error occurred:")
    traceback.print_exc()
