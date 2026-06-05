"""
park_small_house.py
====================
Identical to navigate_to_small_house.py — kept as an alias.
Run either file; they do the same thing.
"""
# Just import and run navigate_to_small_house
import runpy, os
script = os.path.join(os.path.dirname(__file__), "navigate_to_small_house.py")
runpy.run_path(script, run_name="__main__")
