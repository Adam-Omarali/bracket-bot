from openai import OpenAI
import os
from dotenv import load_dotenv
import json

from commands.move import move
from commands.yolo import yolo, yolo_object_found
from commands.move import move_until_close

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
tools = [{
    "type": "function",
    "name": "move",
    "description": "move the robot a given distance and angle",
    "parameters": {
        "type": "object",
        "properties": {
            "distance": {
                "type": "number",
                "description": "Distance to move in meters"
            },
            "angle": {
                "type": "number",
                "description": "Angle to move in degrees"
            }
        },
        "required": [
            "distance",
            "angle"
        ],
        "additionalProperties": False
    }
},
{
    "type": "function",
    "name": "yolo_object_found",
    "description": "Check if an object is found in the current frame.",
    "parameters": {
        "type": "object",
        "properties": {
            "object_name": {
                "type": "string",
                "description": "The name of the object to check for"
            }
        },
        "required": [
            "object_name"
        ],
        "additionalProperties": False
    }
},
{
    "type": "function",
    "name": "move_until_close",
    "description": "Move until the robot is within a given distance of an object.",
    "parameters": {
        "type": "object",
        "properties": {
            "distance": {
                "type": "number",
                "description": "Distance to move in meters"
            }
        },
        "required": [
            "distance"
        ],
        "additionalProperties": False
    }
}
]


def execute_task(task):

    response = client.responses.create(
        model="gpt-4o",
        input=[{"role": "user", "content": f"""
        You are a robot that can move and detect objects.
        Call the appropriate functions to accomplish the given task: {task}
        """}],
        tools=tools
    )

    tool_call = response.output[0]

    if tool_call is None:
        print("No tool call found")
        return
    args = json.loads(tool_call.arguments)

    if tool_call.name == "move":
        move(args["distance"], args["angle"])
    elif tool_call.name == "yolo_object_found":
        yolo_object_found(args["object_name"])
    elif tool_call.name == "move_until_close":
        move_until_close(args["distance"])


if __name__ == "__main__":
    execute_task("move 1 90")