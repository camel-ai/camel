import json
import random
import textwrap
from copy import deepcopy
from typing import Callable, Optional

from tau2.data_model.message import ToolCall
from tau2.data_model.tasks import EnvAssertion, EnvFunctionCall, Task
from tau2.domains.telecom.environment import TelecomEnvironment, get_environment
from tau2.environment.environment import Environment
from tau2.utils import DATA_DIR

from .const import PERSONAS
from .utils import BaseTask, ComposedTask, SelectionSet, compose_tasks


def prepare_base_task(base_task: dict, env: TelecomEnvironment) -> Task:
    base_task = deepcopy(base_task)
    user_name = env.user_tools.db.surroundings.name
    phone_number = env.user_tools.db.surroundings.phone_number
    location = (
        "abroad in France"
        if env.user_tools.db.surroundings.is_abroad
        else "at home in the United States"
    )
    user_info = {"name": user_name, "phone_number": phone_number, "location": location}

    # Update known info based on user info
    known_info_template = base_task["user_scenario"]["instructions"]["known_info"]
    known_info = known_info_template.format(**user_info)
    base_task["user_scenario"]["instructions"]["known_info"] = known_info

    # Update ticket based on user info
    ticket_template = base_task["ticket"]
    ticket = ticket_template.format(**user_info)
    base_task["ticket"] = ticket
    return base_task


class TaskManager:
    def __init__(
        self,
        name: str,
        purpose: str,
        task_instructions: str,
        reason_for_call: str,
        known_info: str,
        ticket: str,
        selection_sets: list[SelectionSet],
        get_env_assertions: Callable[[bool], list[EnvAssertion]],
        set_surrounding: Callable[[Environment], list[EnvFunctionCall]],
        is_fixed: Callable[[Environment], bool],
        task_validator: Optional[Callable[[list[Optional[BaseTask]]], bool]] = None,
        domain: str = "telecom",
    ):
        self.domain = domain
        self.name = name
        self.base_task_template = {
            "id": f"[{name}]",
            "description": {
                "purpose": purpose,
            },
            "user_scenario": {
                "instructions": {
                    "task_instructions": task_instructions,
                    "domain": domain,
                    "reason_for_call": reason_for_call,
                    "known_info": known_info,
                },
                "persona": None,
            },
            "ticket": ticket,
            "initial_state": {},
            "evaluation_criteria": {"env_assertions": None},
        }

        self.selection_sets = selection_sets
        self.get_env_assertions = get_env_assertions
        self.set_surrounding = set_surrounding
        self.is_fixed = is_fixed
        self.task_validator = task_validator

    def create_task(self, composed_task: ComposedTask, persona: str = "None") -> Task:
        env = get_environment()

        init_actions = self.set_surrounding(env)
        env.run_env_function_calls(init_actions)
        for func in composed_task.init_funcs:
            func_calls = func(env)
            env.run_env_function_calls(func_calls)  # env assertion check here
            init_actions.extend(
                # exclude env assertions
                [fc for fc in func_calls if not isinstance(fc, EnvAssertion)]
            )

        fix_tool_calls: list[ToolCall] = []
        expected_failure = False
        for func in composed_task.fix_funcs:
            if func is None:
                expected_failure = True
                break
            tool_calls = func(env)
            fix_tool_calls.extend(tool_calls)

        reward_eval_mode = ["ENV_ASSERTION"]
        if expected_failure:
            fix_actions = [
                {
                    "action_id": "transfer_to_human_agents",
                    "name": "transfer_to_human_agents",
                    "requestor": "assistant",
                    "arguments": {"summary": "I cannot fix the issue."},
                    "compare_args": [],
                }
            ]
            reward_eval_mode.append("ACTION")
        else:
            fix_actions = [
                {
                    "action_id": f"{tc.name}_{i}",
                    "name": tc.name,
                    "requestor": tc.requestor,
                    "arguments": tc.arguments,
                }
                for i, tc in enumerate(fix_tool_calls)
            ]

        env_assertions = self.get_env_assertions(expected_success=not expected_failure)
        if not expected_failure:
            for func in composed_task.extra_env_assertions:
                env_assertions.extend(func(env))

        final_task = prepare_base_task(self.base_task_template, env)
        final_task["initial_state"]["initialization_actions"] = init_actions
        final_task["evaluation_criteria"]["actions"] = fix_actions
        final_task["evaluation_criteria"]["env_assertions"] = env_assertions
        final_task["evaluation_criteria"]["reward_basis"] = reward_eval_mode
        final_task["user_scenario"]["persona"] = PERSONAS[persona]
        final_task["id"] += f"{composed_task.name}[PERSONA:{persona}]"
        final_task["description"]["info"] = composed_task.description
        task = Task(**final_task)
        return task

    def create_tasks(self, save_tasks: bool = False) -> list[Task]:
        composed_tasks = compose_tasks(self.selection_sets, self.task_validator)
        composed_tasks = sorted(composed_tasks, key=lambda x: len(x.composed_from))
        print(f"Number of composed tasks: {len(composed_tasks)}")
        persona_options = list(PERSONAS.keys())
        personas = [
            persona_options[i % len(persona_options)]
            for i in range(len(composed_tasks))
        ]
        tasks = []
        for i, composed_task in enumerate(composed_tasks):
            print(f"Task {i + 1}")
            print(composed_task.name)
            task = self.create_task(composed_task, personas[i])
            print(task)
            print("-" * 100)
            self.verify_task(task)
            print("-" * 100)
            tasks.append(task)
        if save_tasks:
            file = (
                DATA_DIR / "tau2" / "domains" / self.domain / f"{self.name}_tasks.json"
            )
            with open(file, "w") as f:
                json.dump([t.model_dump() for t in tasks], f, indent=2)
        return tasks

    def run_assertions(
        self, env: TelecomEnvironment, task: Task, verbose: bool = False
    ):
        assertions = task.evaluation_criteria.env_assertions or []
        if len(assertions) == 0:
            return True
        success = True
        for i, assertion in enumerate(assertions):
            if verbose:
                print(f"Verifying env assertion {i + 1} of {len(assertions)}")
                print(textwrap.indent(str(assertion), "  "))
            assertion_success = env.run_env_assertion(
                assertion,
                raise_assertion_error=False,
            )
            if verbose:
                print("Success: ", assertion_success)
            success = success and assertion_success
        return success

    def _is_fixable(self, task: Task) -> bool:
        transfer_action_name = "transfer_to_human_agents"
        action_names = {a.name for a in task.evaluation_criteria.actions or []}
        if transfer_action_name in action_names:
            return False
        return True

    def verify_task(self, task: Task):
        from tau2.registry import registry

        print("Verifying task: ", task.id)

        telecom_env = registry.get_env_constructor("telecom")()
        assert self.is_fixed(telecom_env), "Telecom env starts in broken state"
        telecom_env.set_state(
            initialization_data=task.initial_state.initialization_data,
            initialization_actions=task.initial_state.initialization_actions,
            message_history=[],
        )
        fix_actions = task.evaluation_criteria.actions or []
        fixable = self._is_fixable(task)
        for i, action in enumerate(fix_actions):
            assert not self.is_fixed(telecom_env), (
                f"Task {task.id} is already fixed after {i} actions. {task}"
            )
            telecom_env.make_tool_call(
                tool_name=action.name, requestor=action.requestor, **action.arguments
            )
            telecom_env.sync_tools()
        if fixable:
            assert self.is_fixed(telecom_env), (
                f"Task {task.id} is not fixed after all actions. {task}"
            )
        else:
            assert not self.is_fixed(telecom_env), (
                f"Task {task.id} is fixed but should not be. {task}"
            )
        assert self.run_assertions(telecom_env, task, verbose=True)
