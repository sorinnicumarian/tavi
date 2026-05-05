from tavi.agent.gemini_agent import GeminiAgent
from tavi.simulation.simulator import Simulator
from tavi.traces.trace_collector import TraceCollector
from tavi.traces.state_processor import process_state

TASK = "Find the ButterKnife and pick it up."

HINT = (
    "You are already standing near the ButterKnife. "
    "Rotate until ButterKnife appears in your visible objects list, then immediately pick it up. "
    "Do not interact with other objects."
)


def run(sim: Simulator, trace: TraceCollector):
    agent = GeminiAgent(max_steps=30)
    print(f"\n--- LLM agent starting. Task: {TASK} ---")

    knife = sim.navigate_to("Knife")
    if not knife:
        print("  No knife in scene, aborting.")
        return
    knife_id = knife["objectId"]
    print(f"  Teleported near knife ({knife_id})")

    last_outcome = None
    for step in range(agent.max_steps):
        metadata = sim.controller.last_event.metadata
        visible_objects = [o for o in metadata.get("objects", []) if o.get("visible")]
        facts = process_state(metadata)
        all_object_types = sorted({o["objectType"] for o in metadata.get("objects", [])})

        visible_types = [o["objectType"] for o in visible_objects]
        print(f"  [step {step:02d}] visible: {visible_types}")

        action, args = agent.decide(
            visible_objects, facts,
            task=TASK,
            all_object_types=all_object_types,
            last_outcome=last_outcome,
            extra_instructions=HINT,
        )

        if action == "DONE":
            print(f"  Agent signalled DONE after {step} steps.")
            break

        success = trace.step(action, **args)
        last_outcome = "success" if success else "FAILED"
