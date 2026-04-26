from ai2thor.controller import Controller


class Simulator:
    """
    Loads a pre-defined AI2-THOR scene and lets you navigate and interact with it.

    AI2-THOR ships 120+ floor plans — FloorPlan1-30 are kitchens, 201-230 living rooms,
    301-330 bedrooms, 401-430 bathrooms. The layout and objects are fixed per floor plan,
    but their state (open, held, cooked, etc.) changes as the agent acts.

    Full list: https://ai2thor.allenai.org/ithor/documentation/scenes
    """

    def __init__(self, scene: str, width: int = 800, height: int = 600):
        self.controller = Controller(scene=scene, width=width, height=height)
        self.scene = scene
        print(f"Scene loaded: {scene}  (pre-defined AI2-THOR floor plan)")

    def get_objects(self) -> list[dict]:
        return self.controller.last_event.metadata["objects"]

    def navigate_to(self, object_type: str) -> dict | None:
        matches = [o for o in self.get_objects() if object_type in o["objectType"]]
        if not matches:
            print(f"  No {object_type} found in scene.")
            return None

        target = matches[0]
        reachable = self.controller.step("GetReachablePositions").metadata["actionReturn"]
        target_pos = target["position"]
        nearest = min(reachable, key=lambda p: (p["x"] - target_pos["x"])**2 + (p["z"] - target_pos["z"])**2)
        self.controller.step(action="Teleport", position=nearest)
        return target

    def get_visible(self, object_id: str) -> dict | None:
        return next(
            (o for o in self.get_objects() if o["objectId"] == object_id and o["visible"]),
            None,
        )

    def stop(self):
        self.controller.stop()
