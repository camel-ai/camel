import os
import warnings
from dataclasses import dataclass
from typing import Set

from camel.typing import RoleType, TaskType

PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))


# NOTE: Maybe a better solution.
@dataclass
class PromptTemplate:
    template: str
    key_words: Set[str]

    @classmethod
    def get_system_prompt(
        cls,
        task_type: TaskType,
        role_type: RoleType,
    ) -> 'PromptTemplate':
        try:
            template_path = os.path.join(
                PROMPTS_DIR, f"{task_type.value}/{role_type.value}_prompt.txt")
            with open(template_path, "r") as f:
                template = f.read()

            if task_type == TaskType.AI_SOCIETY:
                key_words = set(['<ASSISTANT_ROLE>', "<USER_ROLE>", "<TASK>"])
            if task_type == TaskType.CODE:
                key_words = set(["<LANGUAGE>", "<DOMAIN>", "<TASK>"])
            if task_type == TaskType.MISALIGNMENT:
                key_words = set(['<ASSISTANT_ROLE>', "<USER_ROLE>", "<TASK>"])
            if task_type == TaskType.TRANSLATION:
                key_words = set(["<LANGUAGE>"])
            if task_type == TaskType.DEFAULT:
                key_words = set()

        except ValueError:
            template = "You are a helpful assistant."
            key_words = set()

            warnings.warn("Failed to get system prompt template for "
                          f"task: {task_type.value}, role: {role_type.value}. "
                          f"Set template to: {template}")

        return cls(template, key_words)

    @classmethod
    def get_generate_tasks_prompt(
        cls,
        task_type: TaskType,
    ) -> 'PromptTemplate':
        try:
            template_path = os.path.join(
                PROMPTS_DIR, f"{task_type.value}/generate_tasks.txt")
            with open(template_path, "r") as f:
                template = f.read()

            if task_type == TaskType.AI_SOCIETY:
                key_words = set(
                    ['<NUM_TASKS>', '<ASSISTANT_ROLE>', "<USER_ROLE>"])
            if task_type == TaskType.CODE:
                key_words = set(["<NUM_TASKS>", "<LANGUAGE>", "<DOMAIN>"])
            if task_type == TaskType.MISALIGNMENT:
                key_words = set(
                    ['<NUM_TASKS>', '<ASSISTANT_ROLE>', "<USER_ROLE>"])

            return cls(template, key_words)

        except ValueError:
            raise ValueError(
                "Failed to get generate tasks prompt template for "
                f"task: {task_type.value}.")

    @classmethod
    def get_task_specify_prompt(
        cls,
        task_type: TaskType,
    ) -> 'PromptTemplate':
        try:
            template_path = os.path.join(
                PROMPTS_DIR, f"{task_type.value}/task_specify_prompt.txt")
            with open(template_path, "r") as f:
                template = f.read()

            if task_type == TaskType.AI_SOCIETY:
                key_words = set([
                    '<ASSISTANT_ROLE>', "<USER_ROLE>", "<TASK>", "<WORD_LIMIT>"
                ])
            if task_type == TaskType.CODE:
                key_words = set(
                    ["<LANGUAGE>", "<DOMAIN>", "<TASK>", "<WORD_LIMIT>"])
            if task_type == TaskType.MISALIGNMENT:
                key_words = set([
                    '<ASSISTANT_ROLE>', "<USER_ROLE>", "<TASK>", "<WORD_LIMIT>"
                ])

            return cls(template, key_words)

        except ValueError:
            raise ValueError(
                "Failed to get task task specify prompt template for "
                f"task: {task_type.value}.")
