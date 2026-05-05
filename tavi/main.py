import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

from tavi.simulation.simulator import Simulator
from tavi.traces.trace_collector import TraceCollector
from tavi.simulation.scenarios import scenario_1_hardcoded
from tavi.simulation.scenarios import scenario_2_autonomous

load_dotenv()

# Comment out scenarios you don't want to run
SCENARIOS_TO_RUN = [
    # scenario_1_hardcoded,
    scenario_2_autonomous,
]

SCENE = "FloorPlan1"


if __name__ == "__main__":
    for scenario in SCENARIOS_TO_RUN:
        output = f"traces/{scenario.__name__}.jsonl"
        print(f"\n=== Running {scenario.__name__} ===")

        sim = Simulator(scene=SCENE)
        trace = TraceCollector(sim.controller, output_path=output)
        scenario.run(sim, trace)
        sim.stop()

        print(f"Trace written to: {output}  ({trace.step_id} steps)")
