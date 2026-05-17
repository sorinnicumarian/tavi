from tavi.simulation.scenarios.map_vlm import run_map


def main():

    scene = "FloorPlan1"

    task = "Place a heated glass in a cabinet"

    objs_curr, low_level_plan, sr_step = run_map(scene, task)

    print("\n========== FINAL RESULTS ==========")

    print("\nLow Level Plan:")
    for step in low_level_plan:
        print(step)

    print(f"\nSuccess Rate: {sr_step}")

    print(f"\nFinal Object Count: {len(objs_curr)}")


if __name__ == "__main__":
    main()