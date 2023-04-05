from typing import Dict, Generator, List, Optional, Set, Tuple

from camel.message import SystemMessage, SystemMessageType
from camel.typing import RoleType, TaskType


class SystemMessageGenerator:
    """System message generator for agents.
    """

    def __init__(
        self,
        task_type: Optional[TaskType] = TaskType.AI_SOCIETY,
        sys_prompts: Optional[Dict[RoleType, str]] = None,
        sys_msg_meta_dict_keys: Optional[Set[str]] = None,
    ) -> None:
        if sys_prompts is not None:
            self.sys_prompts = sys_prompts
            self.sys_msg_meta_dict_keys = sys_msg_meta_dict_keys or set()
        else:
            if task_type == TaskType.AI_SOCIETY:
                sys_prompts_paths = {
                    RoleType.ASSISTANT:
                    "prompts/ai_society/assistant_prompt.txt",
                    RoleType.USER: "prompts/ai_society/user_prompt.txt",
                }
                self.sys_msg_meta_dict_keys = {
                    '<ASSISTANT_ROLE>', "<USER_ROLE>", "<TASK>"
                }
            elif task_type == TaskType.CODE:
                sys_prompts_paths = {
                    RoleType.ASSISTANT: "prompts/code/assistant_prompt.txt",
                    RoleType.USER: "prompts/code/user_prompt.txt",
                }
                self.sys_msg_meta_dict_keys = {
                    "<LANGUAGE>", "<DOMAIN>", "<TASK>"
                }
            elif task_type == TaskType.MISALIGNMENT:
                sys_prompts_paths = {
                    RoleType.ASSISTANT:
                    "prompts/misalignment/assistant_prompt.txt",
                    RoleType.USER: "prompts/misalignment/user_prompt.txt",
                }
                self.sys_msg_meta_dict_keys = {
                    '<ASSISTANT_ROLE>', "<USER_ROLE>", "<TASK>"
                }
            elif task_type == TaskType.DEFAULT:
                self.sys_msg_meta_dict_keys = set()
            else:
                raise ValueError(f"Invalid task type: {task_type}")

            self.sys_prompts: Dict[RoleType, str] = dict()
            for key, value in sys_prompts_paths.items():
                with open(value, "r") as f:
                    self.sys_prompts[key] = f.read()

        if RoleType.DEFAULT not in self.sys_prompts:
            self.sys_prompts[RoleType.DEFAULT] = "You are a helpful assistant."

    def validate_meta_dict_keys(self, meta_dict: Dict[str, str]) -> None:
        """Validate the meta_dict keys."""
        if not set(meta_dict.keys()).issubset(self.sys_msg_meta_dict_keys):
            raise ValueError("The keys of the meta_dict should be in "
                             f"{self.sys_msg_meta_dict_keys}. "
                             f"Got {set(meta_dict.keys())} instead.")

    def replace_keywords(
        self,
        meta_dict: Dict[str, str],
        role_type: RoleType,
    ) -> str:
        """Replace keywords in the system prompt."""
        sys_prompt = self.sys_prompts[role_type]
        for key, value in meta_dict.items():
            sys_prompt = sys_prompt.replace(key, value)
        return sys_prompt

    def from_dict(
        self,
        meta_dict: Dict[str, str],
        role_tuple: Tuple[str, RoleType] = ("", RoleType.DEFAULT),
    ) -> SystemMessageType:
        """Generate a system message from a dictionary."""
        self.validate_meta_dict_keys(meta_dict)
        role_name, role_type = role_tuple
        sys_prompt = self.replace_keywords(meta_dict, role_type)
        return SystemMessage(role_name=role_name, role_type=role_type,
                             meta_dict=meta_dict, content=sys_prompt)

    def from_dicts(
        self,
        meta_dicts: List[Dict[str, str]],
        role_tuples: List[Tuple[str, RoleType]],
    ) -> List[SystemMessageType]:
        """Generate a system message from a list of dictionaries."""
        if len(meta_dicts) != len(role_tuples):
            raise ValueError(
                "The number of meta_dicts and role_types should be the same.")

        return [
            self.from_dict(meta_dict, role_tuple)
            for meta_dict, role_tuple in zip(meta_dicts, role_tuples)
        ]


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
