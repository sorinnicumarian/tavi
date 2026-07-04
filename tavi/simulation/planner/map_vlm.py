import numpy as np
from PIL import Image
import io
import base64
import os

from google import genai
from google.genai import types

from tavi.simulation.planner.low_level_planner import LowLevelPlanner
from ai2thor.controller import Controller
from tavi.simulation.planner.utils import gen_low_level_plan, all_objs, execute_low_level_plan
from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
from tavi.rule_generation.src.plain_english.main_english_rule_generator import generate_rules_for_mission
from tavi.rule_generation.src.ltl.main_ltl_template_generation import generate_ltl_templates_for_rules

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

import tavi.simulation.planner.config as planner_config

class Table:

    def get_info_env(self, file_name):
        env_info = ""
        with open(file_name, 'r') as file:
            data = file.readlines()
            for line in data:
                env_info += line
            return env_info
        
class Agents:
    def __init__(self, image, task_description):
        self.encoded_image = image
        self.task_description = task_description

    def ask_gemini(self, prompt, image_base64=None):

        contents = []

        if image_base64 is not None:
            image_bytes = base64.b64decode(image_base64)

            contents = [
                prompt,
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/png",
                )
            ]
        else:
            contents = [prompt]

        response = client.models.generate_content(
            model=planner_config.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=planner_config.GEMINI_MAX_TOKENS,
            )
        )

        return response.text
    
    def single_agent_vision_planning(self):

        prompt = f"""
You are an assistant able to accurately describe the navigation planning steps
required to achieve the goal:

{self.task_description}

You know where the objects are from the image.

Return ONLY atomic navigation steps.
Include movement instructions and object positions.
"""
        return self.ask_gemini(prompt, self.encoded_image)

    def multi_agent_vision_planning(self, objs_from_scene=None):

        env_prompt = f"""
You are an assistant able to analyze an indoor scene.

Task:
{self.task_description}

Objects available in scene:
{objs_from_scene}

Describe:
1. Important objects
2. Relations between objects
3. Instructions useful for solving the task
"""
        enviroment_info = self.ask_gemini(env_prompt, self.encoded_image)

        planning_prompt = f"""
You are a robot planning assistant.

Goal:
{self.task_description}

Scene information:
{enviroment_info}

Generate ONLY atomic navigation/manipulation steps.
Examples:
- walk to sink
- pick glass
- open microwave
- put glass microwave
"""
        plan = self.ask_gemini(planning_prompt)

        return enviroment_info, plan
    
    @staticmethod
    def ndarray_to_base64(img_array: np.ndarray, image_format: str = "PNG") -> str:

        img_array = img_array.astype(np.uint8)
        image = Image.fromarray(img_array)

        buffered = io.BytesIO()
        image.save(buffered, format=image_format)

        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return img_str
    
def run_map(
    scene,
    task,
    trace_collector=None,
    controller=None,
    task_id=None,
    task_record=None,
):
    # if a shared controller is passed in, just reset the scene — no new window
    owns_controller = controller is None
    if owns_controller:
        controller = Controller(scene=scene)
    else:
        controller.reset(scene=scene)

    objs_all = all_objs(controller)

    img = controller.last_event.frame
    agent = Agents(img, task)
    agent.encoded_image = agent.ndarray_to_base64(img)

    env_info, plan = agent.multi_agent_vision_planning(objs_all)

    print("\n===== HIGH LEVEL PLAN =====")
    print(plan)

    low_level_plan = gen_low_level_plan(plan)

    print("\n===== LOW LEVEL PLAN =====")
    for step in low_level_plan:
        print(step)

    print("\n===== ONLINE RULE GENERATION =====")

    rule_output_base = Path(__file__).resolve().parents[2] / "rule_generation" / "outputs"

    if task_id is not None:
        rule_output_base = rule_output_base / f"task_{task_id}"

    generated_rules_dir = generate_rules_for_mission(
        mission_instruction=task,
        high_level_plan=plan,
        low_level_plan=low_level_plan,
        scene_objects=objs_all,
        env_info=env_info,
        task_record=task_record,
        output_dir=rule_output_base,
        debug_output=False,
        revision_rounds=1,
    )

    print(f"Generated mission-specific rules saved to: {generated_rules_dir}")
    
    plain_english_rules_path = generated_rules_dir / "plain_english_rules.json"
    ltl_output_dir = generated_rules_dir

    generated_ltl_dir = generate_ltl_templates_for_rules(
        plain_english_rules_path=plain_english_rules_path,
        output_dir=ltl_output_dir,
    )

    print(f"Generated LTL templates saved to: {generated_ltl_dir}")

    planner = LowLevelPlanner(controller)

    metadata_curr, sr_step = execute_low_level_plan(
        low_level_plan,
        planner,
        trace_collector=trace_collector,
    )

    objs_curr = metadata_curr['objects']

    if owns_controller:
        controller.stop()

    return objs_curr, low_level_plan, sr_step

if __name__ == "__main__":

    scene = 'FloorPlan1'
    task = 'Place a heated glass in a cabinet'

    objs_curr, low_level_plan, sr_step, trajectory = run_map(
        scene=scene_name,
        task=instruction
    )

    print("\n===== SUCCESS RATE =====")
    print(sr_step)