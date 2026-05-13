import numpy as np
from PIL import Image
import io
import base64
import os
import sys

from google import genai
from google.genai import types

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tavi.simulation.scenarios.low_level_planner import LowLevelPlanner
from ai2thor.controller import Controller
from tavi.simulation.scenarios.utils import gen_low_level_plan, all_objs, execute_low_level_plan
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

GEMINI_MODEL = "gemini-2.5-flash"

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
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=500,
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
    trace_collector=None
):

    controller = Controller(scene=scene)

    objs_all = all_objs(controller)

    img = controller.last_event.frame

    agent = Agents(img, task)

    img = agent.ndarray_to_base64(img)

    agent.encoded_image = img

    env_info, plan = agent.multi_agent_vision_planning(objs_all)

    print("\n===== HIGH LEVEL PLAN =====")
    print(plan)

    low_level_plan = gen_low_level_plan(plan)

    print("\n===== LOW LEVEL PLAN =====")
    for step in low_level_plan:
        print(step)

    planner = LowLevelPlanner(controller)

    metadata_curr, sr_step = execute_low_level_plan(
        low_level_plan,
        planner,
        trace_collector=trace_collector
    )

    objs_curr = metadata_curr['objects']

    controller.stop()
    del controller

    return (
        objs_curr,
        low_level_plan,
        sr_step
    )

if __name__ == "__main__":

    scene = 'FloorPlan1'
    task = 'Place a heated glass in a cabinet'

    objs_curr, low_level_plan, sr_step, trajectory = run_map(
        scene=scene_name,
        task=instruction
    )

    print("\n===== SUCCESS RATE =====")
    print(sr_step)