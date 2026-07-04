import numpy as np
from PIL import Image
import io
import base64
import jsonlines
import traceback
from typing import Any
import re
import logging
import time
import random
import copy
from tavi.traces.trace_collector import TraceCollector
from google import genai
from google.genai import types
import os

import tavi.simulation.planner.config as planner_config

def find_obj(controller, obj_type):
    objects = controller.last_event.metadata["objects"]
    for obj in objects:
        if obj["objectType"] == obj_type:
            return obj
    return None


def find_obj_by_type(objects, obj_type):
    for obj in objects:
        if obj["objectType"] == obj_type:
            return obj
    return None


def load_dataset(data_dict, name):
    abstract = True if name == "abstract" else False
    file_path = data_dict[name]
    # keys = ["instruction", "scene_name", "final_state"]
    with jsonlines.open(file_path) as reader:
        data = [line for line in reader]
    
    return_data = []
    if abstract:
        for d in data:
            # import pdb; pdb.set_trace()
            d1, d2, d3, d4 = d.copy(), d.copy(), d.copy(), d.copy()
            d1['instruction'] = d['instruction'][0]
            d2['instruction'] = d['instruction'][1]
            d3['instruction'] = d['instruction'][2]
            d4['instruction'] = d['instruction'][3]
            return_data.append(d1)
            return_data.append(d2)
            return_data.append(d3)
            return_data.append(d4)
    else:
        return_data = data
    
    return return_data


def gen_low_level_plan(high_level_plan: str, model="gpt-4o-mini"):
    sys_prompt = "You are a helpful assistant for a home robot. You are given a high-level plan and need to convert it into a low-level plan."
    prompt = f"""Your task is to rewrite a sequence of high-level plans into a sequence of low-level plan. Each low-level plan has its standard format. Here is the explanation:

1. find obj:
Find the object and the agent will be close to the object. The object needs to be visible.

2. pick obj:
Pick up the object close to the agent. The object needs to be visible and the agent's hand must be clear of obstruction or the action will fail. Picked up objects can also obstruct the Agent's view of the environment since the Agent's hand is always in camera view, so know that picking up larger objects will obstruct the field of vision.

3. put receptacle:
Put down the object that the agent holds into the target receptacle.

4. open obj:
Open the openable object.

5. close obj:
Close the openable object.

6. slice obj:
Slice the sliceable object directly if the agent is close to the object and need not to hold the object. The object will be turned into several new sliced objects called objSliced. But the egg will be broken if sliced.

7. turn on obj:
Turn on the toggleable object if the agent is close to the object.

8. turn off obj:
Turn off the toggleable object if the agent is close to the object.

9. drop:
Drop the pickable object the agent holds. If the object is breakable, the object will be broken after being dropped.

10. throw:
Throw the pickable object the agent holds. If the object is breakable, the object will be broken after being thrown.

11. break obj:
Break the breakable object directly if the agent is close to the object and does not need to hold the object.

12. pour:
Rotate the pickable object the agent holds 90 degrees from the global upward axis. If an object is filled with one of the liquid types, the object will automatically empty itself because the liquid has “spilled.”

13. cook obj:
Cook the cookable object directly if the agent is close to the object and does not need to hold the object. If the cookable object interacts with objects that are heat sources, the object will be turned to the cooked state without using the cook action.

14. dirty obj:
Dirty the dirtyable object directly if the agent is close to the object and does not need to hold the object. 

15. clean obj:
Clean the dirty object directly if the agent is close to the object and does not need to hold the object. 

16. fillLiquid obj water/coffee/wine:
Fill the fillable object with one type of liquid among water/coffee/wine if the agent is close to the object and does not need to hold the object.

17. emptyLiquid obj:
Empty the filled object if the agent is close to the object and does not need to hold the object.

Requirements:
- The low-level plan should be a one of the above formats, one verb one object, without the description of the object.
- if the input high-level plan cannot be converted to a low-level plan, return "Cannot convert the high-level plan to a low-level plan."

Examples:
- Input: "Turn to face the counter to the left of the fridge.\nWalk to the counter.\nPick up the knife from the counter.\nTurn around and walk to the sink.\nWash the knife in the sink.\nDry the knife with a towel.\nReturn to the counter.\nPick up the bread from the counter.\nTurn to face the fridge.\nOpen the fridge.\nPlace the bread inside the fridge.\nClose the fridge."
- Output: "find knife\npick knife\nfind sink\nput sink\nfind bread\nfind fridge\npick bread\nopen fridge\nput fridge\nclose fridge"

Here is the high-level plan you need to convert:
{high_level_plan}

Remember, never generate plans that are not in the standard format, like turn to!

Your low-level plan, remember to follow the standard format:
    """
    low_level_plan = call_gpt(model, prompt, sys_prompt)
    low_level_plan = [line.strip() for line in low_level_plan.split("\n") if line.strip()]
    return low_level_plan


def execute_low_level_plan(
    low_level_plan: list,
    planner,
    trace_output_path=None
):

    num_success_steps = 0

    planner.restore_scene()

    trace_collector = None

    if trace_output_path is not None:

        trace_collector = TraceCollector(
            planner.env,
            trace_output_path
        )

        trace_collector.reset()

    for plan in low_level_plan:

        try:

            pre_metadata = copy.deepcopy(
                planner.env.last_event.metadata
            )

            ret_dict = planner.llm_skill_interact(plan)

            post_metadata = copy.deepcopy(
                planner.env.last_event.metadata
            )

            print(ret_dict)
            print('-' * 50)

            if trace_collector is not None:

                trace_collector.capture_step(
                    action_name=plan,
                    pre_metadata=pre_metadata,
                    post_metadata=post_metadata,
                    success=ret_dict["success"],
                    error=ret_dict.get("errorMessage")
                )

            if ret_dict["success"]:
                num_success_steps += 1

        except Exception as e:

            traceback.print_exc()

    if len(low_level_plan) == 0:
        sr_step = 0
    else:
        sr_step = num_success_steps / len(low_level_plan)

    return (
        planner.env.last_event.metadata,
        sr_step
    )

def execute_low_level_plan(
    low_level_plan: list,
    planner,
    trace_collector=None
):

    num_success_steps = 0

    planner.restore_scene()

    for plan in low_level_plan:

        try:

            pre_metadata = copy.deepcopy(
                planner.env.last_event.metadata
            )

            ret_dict = planner.llm_skill_interact(plan)

            post_metadata = copy.deepcopy(
                planner.env.last_event.metadata
            )

            if trace_collector is not None:

                obj_id = ret_dict.get("objectId")
                trace_collector.capture_step(
                    action_name=plan,
                    action_args={"objectId": obj_id} if obj_id else {},
                    pre_metadata=pre_metadata,
                    post_metadata=post_metadata,
                    success=ret_dict["success"],
                    error=ret_dict.get("errorMessage")
                )

            print(ret_dict)
            print('-' * 50)

            if ret_dict["success"]:
                num_success_steps += 1

        except Exception as e:

            traceback.print_exc()

    if len(low_level_plan) == 0:
        sr_step = 0
    else:
        sr_step = num_success_steps / len(low_level_plan)

    return (
        planner.env.last_event.metadata,
        sr_step
    )

def all_objs(controller):
    objects = controller.last_event.metadata["objects"]
    objects_types = [obj["objectType"] for obj in objects]
    return list(set(objects_types))


def retry_with_exponential_backoff(
        func: Any,
        initial_delay: float = 5,
        exponential_base: float = 2,
        jitter: bool = True,
        max_retries: int = 100,
        errors: Any = (Exception,),
        # errors: Any = (
        #         openai.error.RateLimitError, openai.error.ServiceUnavailableError,
        #         openai.error.APIConnectionError, openai.error.APIError, openai.error.Timeout
        # ),
) -> Any:
    """A wrapper. Retrying a function with exponential backoff."""

    def wrapper(*args, **kwargs):  # type: ignore
        # Initialize variables
        num_retries = 0
        delay = initial_delay
        # Loop until a response or max_retries is hit or an exception is raised.
        while True:
            try:
                logging.debug("calling LLM...")
                return func(*args, **kwargs)

            # Retry on specified errors

            except tuple(errors) as exce:
            # except Exception as exce:
                logging.info(exce._message)
                # Increment retries
                num_retries += 1
                # Check if max retries has been reached
                if num_retries > max_retries:
                    raise Exception(exce) from exce(
                        f"Maximum number of retries ({max_retries}) exceeded."
                    )
                # Increment the delay
                delay *= exponential_base * (1 + jitter * random.random())
                # Sleep for the delay
                time.sleep(delay)
            # Raise exceptions for any errors not specified
            except Exception as e:
                raise e

    return wrapper



@retry_with_exponential_backoff
def call_gpt(
    model,
    prompt,
    system_prompt="You are a helpful assistant.",
    temperature=0.2,
    max_tokens=planner_config.GEMINI_MAX_TOKENS
):

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    full_prompt = f"""
SYSTEM:
{system_prompt}

USER:
{prompt}
"""

    response = client.models.generate_content(
        model=planner_config.GEMINI_MODEL,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
    )

    output = response.text.strip()

    logging.debug("LLM call finished.")

    return output

def call_vllm(prompt, port=9095, model_name="llama3-8b-instruct-hf"):
    client = OpenAI(base_url=f"http://localhost:{port}/v1")
    completion = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "user", "content": prompt},
            ],
        temperature=0.0,
        max_tokens=4096,
        )
    return completion.choices[0].message.content


def call_deepseek(prompt):

    client = OpenAI(api_key="", base_url="https://api.deepseek.com")
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": prompt}
            ],
        stream=False
    )
    logging.debug("LLM call finished.")
    return response.choices[0].message.content


if __name__ == "__main__":
    pass