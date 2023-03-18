from dataclasses import dataclass, field
from typing import Dict, Generator, List, Optional, Sequence, Tuple, Union

from camel_typing import (AssistantSystemMessage, RoleType, SystemMessage,
                          SystemMessageType, UserSystemMessage)


@dataclass
class ChatGPTConfig:
    temperature: float = 0.2  # openai default: 1.0
    top_p: float = 1.0
    n: int = 1
    stream: bool = False
    stop: Optional[Union[str, Sequence[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    logit_bias: Dict = field(default_factory=dict)
    user: str = ""


class SystemMessageGenerator:

    def __init__(
        self,
        with_task: bool = True,
        assistant_role_names_path: str = "data/assistant_roles.txt",
        user_role_names_path: str = "data/user_roles.txt",
        assistant_prompt_path: str = "prompts/assistant_prompt.txt",
        user_prompt_path: str = "prompts/user_prompt.txt",
        assistant_prompt_with_task_path:
        str = "prompts/assistant_prompt_with_task.txt",
        user_task_prompt_with_task_path:
        str = "prompts/user_prompt_with_task.txt",
    ) -> None:
        self.with_task = with_task

        with open(assistant_role_names_path, "r") as f:
            self.assistant_role_names: List[str] = f.read().splitlines()

        with open(user_role_names_path, "r") as f:
            self.user_role_names: List[str] = f.read().splitlines()

        if not self.with_task:
            with open(assistant_prompt_path, "r") as f:
                self.assistant_prompt: str = f.read()

            with open(user_prompt_path, "r") as f:
                self.user_prompt: str = f.read()
        else:
            with open(assistant_prompt_with_task_path, "r") as f:
                self.assistant_prompt: str = f.read()

            with open(user_task_prompt_with_task_path, "r") as f:
                self.user_prompt: str = f.read()

    def from_role(
        self,
        role_name: str = "",
        role_type: RoleType = RoleType.DEFAULT,
        role_prompt: Optional[str] = None,
        task_prompt: Optional[str] = None,
    ) -> SystemMessageType:
        """Generate a system message from a role name and role type."""
        if task_prompt is not None:
            assert self.with_task, "Please set with `with_task=True`."
        if role_type == RoleType.ASSISTANT:
            role_prompt = role_prompt or self.assistant_prompt
            new_role_prompt = role_prompt.replace("<ASSISTANT_ROLE>",
                                                  role_name)
            assert new_role_prompt != role_prompt

            if self.with_task:
                new_role_prompt = new_role_prompt.replace(
                    "<TASK>",
                    task_prompt,
                )

            return AssistantSystemMessage(role_name=role_name,
                                          content=new_role_prompt)

        if role_type == RoleType.USER:
            role_prompt = role_prompt or self.user_prompt
            new_role_prompt = role_prompt.replace("<USER_ROLE>", role_name)
            assert new_role_prompt != role_prompt

            if self.with_task:
                new_role_prompt = new_role_prompt.replace(
                    "<TASK>",
                    task_prompt,
                )

            return UserSystemMessage(role_name=role_name,
                                     content=new_role_prompt)

        if role_type == RoleType.DEFAULT:
            new_role_prompt = role_prompt or "Your are a helpful assistant."
            if task_prompt is not None:
                new_role_prompt = new_role_prompt.replace(
                    "<TASK>", task_prompt)
            return SystemMessage(role_type=role_type, role_name=role_name,
                                 content=new_role_prompt)

    def from_roles(
        self,
        roles: List[Tuple[RoleType, str]],
        assistant_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        task_prompt: Optional[str] = None,
    ) -> List[SystemMessageType]:
        if task_prompt is not None:
            assert self.with_task, "Please set with `with_task=True`."
        assistant_prompt = assistant_prompt or self.assistant_prompt
        user_prompt = user_prompt or self.user_prompt
        role_prompts = [assistant_prompt, user_prompt]
        assert len(roles) == 2, "Only support 1 assistant and 1 user."
        assert RoleType.ASSISTANT in [role_type for _, role_type in roles
                                      ], "Must have 1 assistant."
        assert RoleType.USER in [role_type for _, role_type in roles
                                 ], "Must have 1 user."

        for i, role_prompt in enumerate(role_prompts):
            for role_name, role_type in roles:
                role_prompt = self.from_role(role_name, role_type, role_prompt,
                                             task_prompt).content
            role_prompts[i] = role_prompt

        for role_name, role_type in roles:
            if role_type == RoleType.ASSISTANT:
                assistant_role_name = role_name
            if role_type == RoleType.USER:
                user_role_name = role_name

        assistant_system_message = AssistantSystemMessage(
            role_name=assistant_role_name,
            content=role_prompts[0],
        )
        user_system_message = UserSystemMessage(
            role_name=user_role_name,
            content=role_prompts[1],
        )

        system_messages: List[SystemMessageType] = []
        for _, role_type in roles:
            system_messages.append(assistant_system_message if role_type ==
                                   RoleType.ASSISTANT else user_system_message)

        return system_messages

    # TODO: support task generator as input.
    def from_role_files(
            self) -> Generator[List[SystemMessageType], None, None]:
        for assistant_role_name in self.assistant_role_names:
            for user_role_name in self.user_role_names:
                yield self.from_roles(
                    roles=[(assistant_role_name, RoleType.ASSISTANT),
                           (user_role_name, RoleType.USER)], )


class RoleNameGenerator:

    def __init__(self,
                 assistant_role_names_path: str = "data/assistant_roles.txt",
                 user_role_names_path: str = "data/user_roles.txt") -> None:

        with open(assistant_role_names_path, "r") as f:
            self.assistant_role_names: List[str] = f.read().splitlines()

        with open(user_role_names_path, "r") as f:
            self.user_role_names: List[str] = f.read().splitlines()

    def from_role_files(self) -> Generator[Tuple, None, None]:
        for assistant_role_name in self.assistant_role_names:
            for user_role_name in self.user_role_names:
                yield (assistant_role_name, user_role_name)


class TaskPromptGenerator:

    def __init__(
        self,
        generate_tasks_prompt_path: str = "prompts/generate_tasks.txt",
    ) -> None:

        with open(generate_tasks_prompt_path, "r") as f:
            self.generate_tasks_prompt: str = f.read()

    def from_role_files(
        self,
        assistant_role_names_path: str = "data/assistant_roles.txt",
        user_role_names_path: str = "data/user_roles.txt"
    ) -> Generator[str, None, None]:
        roles_generator = RoleNameGenerator(
            assistant_role_names_path, user_role_names_path).from_role_files()
        for role_1, role_2 in roles_generator:
            yield (self.generate_tasks_prompt.replace("<ROLE_1>",
                                                      role_1).replace(
                                                          "<ROLE_2>", role_2))

    def from_role_generator(
        self, role_generator: Generator[Tuple, None, None]
    ) -> Generator[str, None, None]:
        for role_1, role_2 in role_generator:
            yield (self.generate_tasks_prompt.replace("<ROLE_1>",
                                                      role_1).replace(
                                                          "<ROLE_2>", role_2))


if __name__ == "__main__":
    sys_msg_generator = SystemMessageGenerator(with_task=False)
    sys_msg_generator.from_role(role_name="doctor",
                                role_type=RoleType.ASSISTANT)
    sys_msg_generator.from_role(role_name="doctor", role_type=RoleType.USER)

    sys_msg_generator.from_roles(
        roles=[("doctor", RoleType.USER), ("chatbot", RoleType.ASSISTANT)])

    generator = sys_msg_generator.from_role_files()
    sys_msg_1 = next(generator)
    sys_msg_2 = next(generator)
    assert sys_msg_1 != sys_msg_2

    sys_msg_generator = SystemMessageGenerator(with_task=True)
    sys_msg_generator.from_roles(
        roles=[("doctor", RoleType.USER), ("chatbot", RoleType.ASSISTANT)],
        task_prompt="Analyze a patient's medical report")

    role_name_generator = RoleNameGenerator().from_role_files()
    role_tuple = next(role_name_generator)
    assert isinstance(role_tuple, tuple)
    
    task_tuple = next(TaskPromptGenerator().generate_role_prompt())
    assert isinstance(task_tuple, str)

