from typing import Generator, List, Optional, Tuple

from camel.message import (AssistantSystemMessage, RoleType, SystemMessage,
                           SystemMessageType, UserSystemMessage)


class SystemMessageGenerator:

    def __init__(
        self,
        with_task: bool = True,
        assistant_role_names_path: str = "data/ai_society/assistant_roles.txt",
        user_role_names_path: str = "data/ai_society/user_roles.txt",
        assistant_prompt_path: str = "prompts/ai_society/assistant_prompt.txt",
        user_prompt_path: str = "prompts/ai_society/user_prompt.txt",
        assistant_prompt_with_task_path:
        str = "prompts/ai_society/assistant_prompt_with_task.txt",
        user_task_prompt_with_task_path:
        str = "prompts/ai_society/user_prompt_with_task.txt",
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
            new_role_prompt = role_prompt or "You are a helpful assistant."
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

    def __init__(
        self,
        assistant_role_names_path: str = "data/ai_society/assistant_roles.txt",
        user_role_names_path: str = "data/ai_society/user_roles.txt",
    ) -> None:

        with open(assistant_role_names_path, "r") as f:
            assistant_role_names: List[str] = f.read().splitlines()
            self.assistant_role_names = [
                " ".join(name.split(" ")[1:]) for name in assistant_role_names
            ]

        with open(user_role_names_path, "r") as f:
            user_role_names: List[str] = f.read().splitlines()
            self.user_role_names = [
                " ".join(name.split(" ")[1:]) for name in user_role_names
            ]

    def from_role_files(self) -> Generator[Tuple, None, None]:
        for assistant_role_name in self.assistant_role_names:
            for user_role_name in self.user_role_names:
                yield (assistant_role_name, user_role_name)


class AISocietyTaskPromptGenerator:

    def __init__(
        self,
        generate_tasks_prompt_path:
        str = "prompts/ai_society/generate_tasks.txt",
        num_tasks: int = 10,
    ) -> None:

        with open(generate_tasks_prompt_path, "r") as f:
            self.generate_tasks_prompt: str = f.read()

        self.num_tasks = num_tasks

    # TODO: Return role names for user and assistant with the generator.
    def from_role_files(
        self,
        assistant_role_names_path: str = "data/ai_society/assistant_roles.txt",
        user_role_names_path: str = "data/ai_society/user_roles.txt"
    ) -> Generator[str, None, None]:
        roles_generator = RoleNameGenerator(
            assistant_role_names_path, user_role_names_path).from_role_files()
        for role_1, role_2 in roles_generator:
            yield (self.generate_tasks_prompt.replace(
                "<ROLE_1>",
                role_1).replace("<ROLE_2>",
                                role_2).replace("<NUM_TASKS>",
                                                str(self.num_tasks)))

    def from_role_generator(
        self, role_generator: Generator[Tuple, None, None]
    ) -> Generator[str, None, None]:
        for role_1, role_2 in role_generator:
            yield (self.generate_tasks_prompt.replace("<ROLE_1>",
                                                      role_1).replace(
                                                          "<ROLE_2>", role_2))


class SingleTxtGenerator:

    def __init__(
        self,
        text_file_path: str,
    ) -> None:

        with open(text_file_path, "r") as f:
            data_list: List[str] = f.read().splitlines()
            self.data_list = [
                " ".join(name.split(" ")[1:]) for name in data_list
            ]

    def from_role_files(self) -> Generator[Tuple, None, None]:
        for data in self.data_list:
            yield data


class CodeTaskPromptGenerator:

    def __init__(
        self,
        generate_tasks_prompt_path: str = "prompts/code/generate_tasks.txt",
        num_tasks: int = 50,
    ) -> None:

        with open(generate_tasks_prompt_path, "r") as f:
            self.generate_tasks_prompt: str = f.read()

        self.num_tasks = num_tasks

    def from_role_files(
        self, languages_path: str = "data/code/languages.txt",
        domains_path: str = "data/code/domains.txt"
    ) -> Generator[Tuple[str, str, str], None, None]:
        language_generator = SingleTxtGenerator(
            languages_path).from_role_files()

        for language in language_generator:
            domains_generator = SingleTxtGenerator(
                domains_path).from_role_files()
            for domain in domains_generator:
                generated_tasks_prompt = self.generate_tasks_prompt.replace(
                    "<LANGUAGE>",
                    language).replace("<DOMAIN>",
                                      domain).replace("<NUM_TASKS>",
                                                      str(self.num_tasks))
                yield (generated_tasks_prompt, language, domain)

    def from_role_generator(
        self, role_generator: Generator[Tuple, None, None]
    ) -> Generator[str, None, None]:
        raise NotImplementedError
