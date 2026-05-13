import os
import jsonlines
import traceback

from tavi.simulation.scenarios.map_vlm import run_map
from tavi.traces.trace_collector import TraceCollector


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

input_file = os.path.join(
    BASE_DIR,
    "abstract_1009.jsonl"
)

output_file = os.path.join(
    BASE_DIR,
    "abstract_traces.jsonl"
)


def main():
    # clear old traces file
    open(output_file, "w").close()
    
    with jsonlines.open(input_file) as reader:

        for idx, sample in enumerate(reader):

            try:

                print(f"\n========== SAMPLE {idx} ==========")

                instruction = sample.get("instruction")

                scene_name = sample.get("scene_name")

                if isinstance(instruction, list):
                    instruction = instruction[0]

                trace_collector = TraceCollector(
                    output_path=output_file,
                    episode_id=idx,
                    scene_name=scene_name,
                    instruction=instruction
                )

                objs_curr, low_level_plan, sr_step = run_map(
                    scene=scene_name,
                    task=instruction,
                    trace_collector=trace_collector
                )

                print(
                    f"Finished sample {idx} "
                    f"with SR={sr_step}"
                )

            except Exception as e:

                traceback.print_exc()

                continue


if __name__ == "__main__":
    main()