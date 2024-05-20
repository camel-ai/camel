# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import importlib
import os
import platform
import re
import socket
import time
import zipfile
from functools import wraps
from typing import Any, Callable, List, Optional, Set, TypeVar, cast
from urllib.parse import urlparse

import pydantic
import requests

from camel.types import TaskType

F = TypeVar('F', bound=Callable[..., Any])


# Set lazy import
def get_lazy_imported_functions_module():
    from camel.functions import (
        MAP_FUNCS,
        MATH_FUNCS,
        OPENAPI_FUNCS,
        SEARCH_FUNCS,
        TWITTER_FUNCS,
        WEATHER_FUNCS,
    )

    return [
        *MATH_FUNCS,
        *SEARCH_FUNCS,
        *WEATHER_FUNCS,
        *MAP_FUNCS,
        *TWITTER_FUNCS,
        *OPENAPI_FUNCS,
    ]


# Set lazy import
def get_lazy_imported_types_module():
    from camel.types import ModelType

    return ModelType.GPT_3_5_TURBO


def api_key_required(func: F) -> F:
    r"""Decorator that checks if the OpenAI API key is available in the
    environment variables.

    Args:
        func (callable): The function to be wrapped.

    Returns:
        callable: The decorated function.

    Raises:
        ValueError: If the OpenAI API key is not found in the environment
            variables.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.model_type.is_openai:
            if 'OPENAI_API_KEY' not in os.environ:
                raise ValueError('OpenAI API key not found.')
            return func(self, *args, **kwargs)
        elif self.model_type.is_anthropic:
            if 'ANTHROPIC_API_KEY' not in os.environ:
                raise ValueError('Anthropic API key not found.')
            return func(self, *args, **kwargs)
        else:
            raise ValueError('Unsupported model type.')

    return cast(F, wrapper)


def print_text_animated(text, delay: float = 0.02, end: str = ""):
    r"""Prints the given text with an animated effect.

    Args:
        text (str): The text to print.
        delay (float, optional): The delay between each character printed.
            (default: :obj:`0.02`)
        end (str, optional): The end character to print after each
            character of text. (default: :obj:`""`)
    """
    for char in text:
        print(char, end=end, flush=True)
        time.sleep(delay)
    print('\n')


def get_prompt_template_key_words(template: str) -> Set[str]:
    r"""Given a string template containing curly braces {}, return a set of
    the words inside the braces.

    Args:
        template (str): A string containing curly braces.

    Returns:
        List[str]: A list of the words inside the curly braces.

    Example:
        >>> get_prompt_template_key_words('Hi, {name}! How are you {status}?')
        {'name', 'status'}
    """
    return set(re.findall(r'{([^}]*)}', template))


def get_first_int(string: str) -> Optional[int]:
    r"""Returns the first integer number found in the given string.

    If no integer number is found, returns None.

    Args:
        string (str): The input string.

    Returns:
        int or None: The first integer number found in the string, or None if
            no integer number is found.
    """
    match = re.search(r'\d+', string)
    if match:
        return int(match.group())
    else:
        return None


def download_tasks(task: TaskType, folder_path: str) -> None:
    r"""Downloads task-related files from a specified URL and extracts them.

    This function downloads a zip file containing tasks based on the specified
    `task` type from a predefined URL, saves it to `folder_path`, and then
    extracts the contents of the zip file into the same folder. After
    extraction, the zip file is deleted.

    Args:
        task (TaskType): An enum representing the type of task to download.
        folder_path (str): The path of the folder where the zip file will be
                           downloaded and extracted.
    """
    # Define the path to save the zip file
    zip_file_path = os.path.join(folder_path, "tasks.zip")

    # Download the zip file from the Google Drive link
    response = requests.get(
        "https://huggingface.co/datasets/camel-ai/"
        f"metadata/resolve/main/{task.value}_tasks.zip"
    )

    # Save the zip file
    with open(zip_file_path, "wb") as f:
        f.write(response.content)

    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
        zip_ref.extractall(folder_path)

    # Delete the zip file
    os.remove(zip_file_path)


def get_task_list(task_response: str) -> List[str]:
    r"""Parse the response of the Agent and return task list.

    Args:
        task_response (str): The string response of the Agent.

    Returns:
        List[str]: A list of the string tasks.
    """

    new_tasks_list = []
    task_string_list = task_response.strip().split('\n')
    # each task starts with #.
    for task_string in task_string_list:
        task_parts = task_string.strip().split(".", 1)
        if len(task_parts) == 2:
            task_id = ''.join(s for s in task_parts[0] if s.isnumeric())
            task_name = re.sub(r'[^\w\s_]+', '', task_parts[1]).strip()
            if task_name.strip() and task_id.isnumeric():
                new_tasks_list.append(task_name)
    return new_tasks_list


def check_server_running(server_url: str) -> bool:
    r"""Check whether the port refered by the URL to the server
    is open.

    Args:
        server_url (str): The URL to the server running LLM inference
            service.

    Returns:
        bool: Whether the port is open for packets (server is running).
    """
    parsed_url = urlparse(server_url)
    url_tuple = (parsed_url.hostname, parsed_url.port)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(url_tuple)
    sock.close()

    # if the port is open, the result should be 0.
    return result == 0


def dependencies_required(*required_modules: str) -> Callable[[F], F]:
    r"""A decorator to ensure that specified Python modules
    are available before a function executes.

    Args:
        required_modules (str): The required modules to be checked for
            availability.

    Returns:
        Callable[[F], F]: The original function with the added check for
            required module dependencies.

    Raises:
        ImportError: If any of the required modules are not available.

    Example:
        ::

            @dependencies_required('numpy', 'pandas')
            def data_processing_function():
                # Function implementation...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            missing_modules = [
                m for m in required_modules if not is_module_available(m)
            ]
            if missing_modules:
                raise ImportError(
                    f"Missing required modules: {', '.join(missing_modules)}"
                )
            return func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


def is_module_available(module_name: str) -> bool:
    r"""Check if a module is available for import.

    Args:
        module_name (str): The name of the module to check for availability.

    Returns:
        bool: True if the module can be imported, False otherwise.
    """
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def api_keys_required(*required_keys: str) -> Callable[[F], F]:
    r"""A decorator to check if the required API keys are
    present in the environment variables.

    Args:
        required_keys (str): The required API keys to be checked.

    Returns:
        Callable[[F], F]: The original function with the added check
            for required API keys.

    Raises:
        ValueError: If any of the required API keys are missing in the
            environment variables.

    Example:
        ::

            @api_keys_required('API_KEY_1', 'API_KEY_2')
            def some_api_function():
                # Function implementation...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            missing_keys = [k for k in required_keys if k not in os.environ]
            if missing_keys:
                raise ValueError(f"Missing API keys: {', '.join(missing_keys)}")
            return func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


def get_system_information():
    r"""Gathers information about the operating system.

    Returns:
        dict: A dictionary containing various pieces of OS information.
    """
    sys_info = {
        "OS Name": os.name,
        "System": platform.system(),
        "Release": platform.release(),
        "Version": platform.version(),
        "Machine": platform.machine(),
        "Processor": platform.processor(),
        "Platform": platform.platform(),
    }

    return sys_info


def to_pascal(snake: str) -> str:
    """Convert a snake_case string to PascalCase.

    Args:
        snake (str): The snake_case string to be converted.

    Returns:
        str: The converted PascalCase string.
    """
    # Check if the string is already in PascalCase
    if re.match(r'^[A-Z][a-zA-Z0-9]*([A-Z][a-zA-Z0-9]*)*$', snake):
        return snake
    # Remove leading and trailing underscores
    snake = snake.strip('_')
    # Replace multiple underscores with a single one
    snake = re.sub('_+', '_', snake)
    # Convert to PascalCase
    return re.sub(
        '_([0-9A-Za-z])',
        lambda m: m.group(1).upper(),
        snake.title(),
    )


PYDANTIC_V2 = pydantic.VERSION.startswith("2.")


def role_playing_with_function(
    task_prompt: str = (
        "Assume now is 2024 in the Gregorian calendar, "
        "estimate the current age of University of Oxford "
        "and then add 10 more years to this age, "
        "and get the current weather of the city where "
        "the University is located. And tell me what time "
        "zone University of Oxford is in. And use my twitter "
        "account infomation to create a tweet. Search basketball"
        "course from coursera And help me to choose a basketball by klarna."
    ),
    function_list: Optional[List] = None,
    model_type=None,
    chat_turn_limit=10,
    assistant_role_name: str = "Searcher",
    user_role_name: str = "Professor",
) -> None:
    r"""Initializes and conducts a `RolePlaying` with `FunctionCallingConfig`
    session. The function creates an interactive and dynamic role-play session
    where the AI Assistant and User engage based on the given task, roles, and
    available functions. It demonstrates the versatility of AI in handling
    diverse tasks and user interactions within a structured `RolePlaying`
    framework.

    Args:
        task_prompt (str): The initial task or scenario description to start
            the `RolePlaying` session. Defaults to a prompt involving the
            estimation of KAUST's age and weather information.
        function_list (list): A list of functions that the agent can utilize
            during the session. Defaults to a combination of math, search, and
            weather functions.
        model_type (ModelType): The type of chatbot model used for both the
            assistant and the user. Defaults to `GPT-4 Turbo`.
        chat_turn_limit (int): The maximum number of turns (exchanges) in the
            chat session. Defaults to 10.
        assistant_role_name (str): The role name assigned to the AI Assistant.
            Defaults to 'Searcher'.
        user_role_name (str): The role name assigned to the User. Defaults to
            'Professor'.

    Returns:
        None: This function does not return any value but prints out the
            session's dialogues and outputs.
    """

    # Run lazy import
    if function_list is None:
        function_list = get_lazy_imported_functions_module()
    if model_type is None:
        model_type = get_lazy_imported_types_module()

    from colorama import Fore

    from camel.agents.chat_agent import FunctionCallingRecord
    from camel.configs import ChatGPTConfig, FunctionCallingConfig
    from camel.societies import RolePlaying

    task_prompt = task_prompt
    user_model_config = ChatGPTConfig(temperature=0.0)

    function_list = function_list
    assistant_model_config = FunctionCallingConfig.from_openai_function_list(
        function_list=function_list,
        kwargs=dict(temperature=0.0),
    )

    role_play_session = RolePlaying(
        assistant_role_name=assistant_role_name,
        user_role_name=user_role_name,
        assistant_agent_kwargs=dict(
            model_type=model_type,
            model_config=assistant_model_config,
            function_list=function_list,
        ),
        user_agent_kwargs=dict(
            model_type=model_type,
            model_config=user_model_config,
        ),
        task_prompt=task_prompt,
        with_task_specify=False,
    )

    print(
        Fore.GREEN
        + f"AI Assistant sys message:\n{role_play_session.assistant_sys_msg}\n"
    )
    print(
        Fore.BLUE + f"AI User sys message:\n{role_play_session.user_sys_msg}\n"
    )

    print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
    print(
        Fore.CYAN
        + f"Specified task prompt:\n{role_play_session.specified_task_prompt}\n"
    )
    print(Fore.RED + f"Final task prompt:\n{role_play_session.task_prompt}\n")

    n = 0
    input_msg = role_play_session.init_chat()
    while n < chat_turn_limit:
        n += 1
        assistant_response, user_response = role_play_session.step(input_msg)

        if assistant_response.terminated:
            print(
                Fore.GREEN
                + (
                    "AI Assistant terminated. Reason: "
                    f"{assistant_response.info['termination_reasons']}."
                )
            )
            break
        if user_response.terminated:
            print(
                Fore.GREEN
                + (
                    "AI User terminated. "
                    f"Reason: {user_response.info['termination_reasons']}."
                )
            )
            break

        # Print output from the user
        print_text_animated(
            Fore.BLUE + f"AI User:\n\n{user_response.msg.content}\n"
        )

        # Print output from the assistant, including any function
        # execution information
        print_text_animated(Fore.GREEN + "AI Assistant:")
        called_functions: List[FunctionCallingRecord] = assistant_response.info[
            'called_functions'
        ]
        for func_record in called_functions:
            print_text_animated(f"{func_record}")
        print_text_animated(f"{assistant_response.msg.content}\n")

        if "CAMEL_TASK_DONE" in user_response.msg.content:
            break

        input_msg = assistant_response.msg
