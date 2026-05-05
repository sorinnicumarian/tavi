import time

from tavi.simulation.simulator import Simulator
from tavi.traces.trace_collector import TraceCollector


def run(sim: Simulator, trace: TraceCollector):
    print("\n--- Moving around ---")
    trace.step("RotateRight")
    trace.step("RotateRight")
    trace.step("RotateLeft")
    trace.step("MoveAhead")
    trace.step("MoveAhead")

    print("\n--- Navigating to knife ---")
    knife = sim.navigate_to("Knife")

    if not knife:
        return

    degrees_per_rotation = 90
    full_rotation = 360
    max_rotation_attempts = (full_rotation // degrees_per_rotation) * 2  # two full turns for partial occlusion

    visible_knife = None
    for _ in range(max_rotation_attempts):
        visible_knife = sim.get_visible(knife["objectId"])
        if visible_knife:
            break
        trace.step("RotateRight")

    if visible_knife:
        print(f"  Found {visible_knife['objectType']}")
        trace.step("PickupObject", objectId=visible_knife["objectId"])
        time.sleep(0.5)
        trace.step("DropHandObject")
    else:
        print("  Knife in scene but couldn't get line of sight.")
