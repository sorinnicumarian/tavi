import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import argparse

from tavi.simulation.simulator import Simulator
from tavi.traces.trace_collector import TraceCollector
from tavi.simulation.scenarios import simple_scenario_1


def main(scene: str, output: str):
    sim = Simulator(scene=scene)
    trace = TraceCollector(sim.controller, output_path=output)

    simple_scenario_1.run(sim, trace)

    sim.stop()
    print(f"\nTrace written to: {output}  ({trace.step_id} steps)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", default="FloorPlan1")
    parser.add_argument("--output", default="traces/run.jsonl")
    args = parser.parse_args()
    main(args.scene, args.output)
