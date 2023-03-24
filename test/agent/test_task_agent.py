import os

from camel.agent import TaskPlannerAgent, TaskSpecifyAgent
from camel.configs import ChatGPTConfig
from camel.typing import ModeType, TaskType

assert os.environ.get("OPENAI_API_KEY") is not None, "Missing OPENAI_API_KEY"


def test_task_specify_ai_society_agent():
    original_task_prompt = "Improving stage presence and performance skills"
    print(f"Original task prompt:\n{original_task_prompt}\n")
    task_specify_agent = TaskSpecifyAgent(
        ModeType.GPT_3_5_TURBO, model_config=ChatGPTConfig(temperature=1.0))
    specified_task_prompt = task_specify_agent.specify_task(
        original_task_prompt, [
            ("<ASSISTANT_ROLE>", "Musician"),
            ("<USER_ROLE>", "Student"),
        ])
    print(f"Specified task prompt:\n{specified_task_prompt}\n")


def test_task_specify_code_agent():
    original_task_prompt = "Modeling molecular dynamics"
    print(f"Original task prompt:\n{original_task_prompt}\n")
    task_specify_agent = TaskSpecifyAgent(
        ModeType.GPT_3_5_TURBO,
        task_type=TaskType.CODE,
        model_config=ChatGPTConfig(temperature=1.0),
    )
    specified_task_prompt = task_specify_agent.specify_task(
        original_task_prompt, [
            ("<DOMAIN>", "Chemistry"),
            ("<LANGUAGE>", "Python"),
        ])
    print(f"Specified task prompt:\n{specified_task_prompt}\n")


def test_task_planner_agent():
    original_task_prompt = "Modeling molecular dynamics"
    print(f"Original task prompt:\n{original_task_prompt}\n")
    task_specify_agent = TaskSpecifyAgent(
        ModeType.GPT_3_5_TURBO,
        task_type=TaskType.CODE,
        model_config=ChatGPTConfig(temperature=1.0),
    )
    specified_task_prompt = task_specify_agent.specify_task(
        original_task_prompt, [
            ("<DOMAIN>", "Chemistry"),
            ("<LANGUAGE>", "Python"),
        ])
    print(f"Specified task prompt:\n{specified_task_prompt}\n")
    task_planner_agent = TaskPlannerAgent(
        ModeType.GPT_3_5_TURBO, model_config=ChatGPTConfig(temperature=1.0))
    planned_task_prompt = task_planner_agent.plan_task(specified_task_prompt)
    print(f"Planned task prompt:\n{planned_task_prompt}\n")
