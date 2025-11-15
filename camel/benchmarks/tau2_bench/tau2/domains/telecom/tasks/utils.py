import re
from itertools import product
from typing import Callable, Optional

from pydantic import BaseModel, Field

from tau2.data_model.message import ToolCall
from tau2.data_model.tasks import EnvAssertion, EnvFunctionCall
from tau2.environment.environment import Environment

InitFuncType = Callable[[Environment], list[EnvFunctionCall | EnvAssertion]]
FixFuncType = Callable[[Environment], list[ToolCall]] | None
EnvAssertionType = Callable[[Environment], list[EnvAssertion]]


class BaseTask(BaseModel):
    name: str
    description: str
    init_funcs: list[InitFuncType]
    fix_funcs: list[FixFuncType]
    extra_env_assertions: list[EnvAssertionType] = Field(default_factory=list)


class SelectionSet(BaseModel):
    tasks: list[BaseTask]


class ComposedTask(BaseModel):
    name: str
    description: str
    composed_from: list[BaseTask]
    init_funcs: list[InitFuncType]
    fix_funcs: list[FixFuncType]
    extra_env_assertions: list[EnvAssertionType] = Field(default_factory=list)

    def __str__(self):
        lines = []
        lines.append("-" * len(self.name))
        lines.append(self.name)
        lines.append("-" * len(self.name))
        lines.append(f"Description: {self.description}")
        lines.append("Base Tasks:")
        for task in self.composed_from:
            lines.append(f"  - {task.name}: {task.description}")
        lines.append("Init Funcs:")
        for func in self.init_funcs:
            lines.append(f"  - {func.__name__}")
        lines.append("Fix Funcs:")
        for func in self.fix_funcs:
            lines.append(f"  - {func.__name__}")
        lines.append("Extra Env Assertions:")
        for func in self.extra_env_assertions:
            lines.append(f"  - {func.__name__}")

        return "\n".join(lines)

    def __repr__(self):
        return self.__str__()


def compose_tasks(
    selection_sets: list[SelectionSet],
    task_validator: Optional[Callable[[list[Optional[BaseTask]]], bool]] = None,
) -> list[ComposedTask]:
    """
    Return all the combinations of selecting 0 or more tasks from the selection sets
    """

    product_tasks = list(
        product(*[selection_set.tasks + [None] for selection_set in selection_sets])
    )
    composed_tasks = []
    for tasks in product_tasks:
        if task_validator is not None:
            if not task_validator(tasks):
                continue
        tasks = sorted([t for t in tasks if t is not None], key=lambda x: x.name)
        if task_validator is None and len(tasks) == 0:
            continue
        init_funcs = [f for t in tasks for f in t.init_funcs]
        fix_funcs = [f for t in tasks for f in t.fix_funcs]
        extra_env_assertions = [f for t in tasks for f in t.extra_env_assertions]
        composed_task = ComposedTask(
            name="|".join([t.name for t in tasks]),
            description=", ".join([t.description for t in tasks]),
            composed_from=tasks,
            init_funcs=init_funcs,
            fix_funcs=fix_funcs,
            extra_env_assertions=extra_env_assertions,
        )
        composed_tasks.append(composed_task)
    return composed_tasks


def get_intent_from_task_id(task_id: str) -> str:
    """
    Extract the intent from the task_id.
    task_id is of the form: [intent]action1|action2|...|actionk[PERSONA:persona]
    """
    pat = r"^\[([a-zA-Z_]+)\]"
    match = re.search(pat, task_id)
    if match:
        return match.group(1)
    else:
        raise ValueError(f"Could not extract intent from task_id: {task_id}")


def get_persona_from_task_id(task_id: str) -> str:
    """
    Extract the persona from the task_id.
    task_id is of the form: [intent]action1|action2|...|actionk[PERSONA:persona]
    """
    pat = r"\[PERSONA:([a-zA-Z_]+)\]"
    match = re.search(pat, task_id)
    if match:
        return match.group(1)
    else:
        raise ValueError(f"Could not extract intent from task_id: {task_id}")


def get_num_issues_from_task_id(task_id: str) -> int:
    """
    Extract the number of issues from the task_id.
    task_id is of the form: [intent]action1|action2|...|actionk[PERSONA:persona]
    """
    return len(task_id.split("|"))
