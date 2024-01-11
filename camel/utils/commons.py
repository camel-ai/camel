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
import inspect
import os
import re
import socket
import time
import zipfile
from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    cast,
)
from urllib.parse import urlparse

import requests

from camel.types import TaskType

F = TypeVar('F', bound=Callable[..., Any])


# Set lazy import
def get_lazy_imported_functions_module():
    from camel.functions import MATH_FUNCS, SEARCH_FUNCS, WEATHER_FUNCS
    return [*MATH_FUNCS, *SEARCH_FUNCS, *WEATHER_FUNCS]


def get_lazy_imported_types_module():
    from camel.types import ModelType
    return ModelType.GPT_4_TURBO


def openai_api_key_required(func: F) -> F:
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
        if 'OPENAI_API_KEY' in os.environ:
            return func(self, *args, **kwargs)
        else:
            raise ValueError('OpenAI API key not found.')

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
    # Define the path to save the zip file
    zip_file_path = os.path.join(folder_path, "tasks.zip")

    # Download the zip file from the Google Drive link
    response = requests.get("https://huggingface.co/datasets/camel-ai/"
                            f"metadata/resolve/main/{task.value}_tasks.zip")

    # Save the zip file
    with open(zip_file_path, "wb") as f:
        f.write(response.content)

    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
        zip_ref.extractall(folder_path)

    # Delete the zip file
    os.remove(zip_file_path)


def parse_doc(func: Callable) -> Dict[str, Any]:
    r"""Parse the docstrings of a function to extract the function name,
    description and parameters.

    Args:
        func (Callable): The function to be parsed.
    Returns:
        Dict[str, Any]: A dictionary with the function's name,
            description, and parameters.
    """

    doc = inspect.getdoc(func)
    if not doc:
        raise ValueError(
            f"Invalid function {func.__name__}: no docstring provided.")

    properties = {}
    required = []

    parts = re.split(r'\n\s*\n', doc)
    func_desc = parts[0].strip()

    args_section = next((p for p in parts if 'Args:' in p), None)
    if args_section:
        args_descs: List[Tuple[str, str, str, ]] = re.findall(
            r'(\w+)\s*\((\w+)\):\s*(.*)', args_section)
        properties = {
            name.strip(): {
                'type': type,
                'description': desc
            }
            for name, type, desc in args_descs
        }
        for name in properties:
            required.append(name)

    # Parameters from the function signature
    sign_params = list(inspect.signature(func).parameters.keys())
    if len(sign_params) != len(required):
        raise ValueError(
            f"Number of parameters in function signature ({len(sign_params)})"
            f" does not match that in docstring ({len(required)}).")

    for param in sign_params:
        if param not in required:
            raise ValueError(f"Parameter '{param}' in function signature"
                             " is missing in the docstring.")

    parameters = {
        "type": "object",
        "properties": properties,
        "required": required,
    }

    # Construct the function dictionary
    function_dict = {
        "name": func.__name__,
        "description": func_desc,
        "parameters": parameters,
    }

    return function_dict


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


def role_playing_with_function(
    task_prompt: str = ("Assuming the current year is 2023, estimate KAUST's "
                        "current age and then add 10 more years to this age, "
                        "and get the current weather of the city where KAUST "
                        "is located."),
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
        Fore.GREEN +
        f"AI Assistant sys message:\n{role_play_session.assistant_sys_msg}\n")
    print(Fore.BLUE +
          f"AI User sys message:\n{role_play_session.user_sys_msg}\n")

    print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
    print(
        Fore.CYAN +
        f"Specified task prompt:\n{role_play_session.specified_task_prompt}\n")
    print(Fore.RED + f"Final task prompt:\n{role_play_session.task_prompt}\n")

    n = 0
    input_assistant_msg, _ = role_play_session.init_chat()
    while n < chat_turn_limit:
        n += 1
        assistant_response, user_response = role_play_session.step(
            input_assistant_msg)

        if assistant_response.terminated:
            print(Fore.GREEN +
                  ("AI Assistant terminated. Reason: "
                   f"{assistant_response.info['termination_reasons']}."))
            break
        if user_response.terminated:
            print(Fore.GREEN +
                  ("AI User terminated. "
                   f"Reason: {user_response.info['termination_reasons']}."))
            break

        # Print output from the user
        print_text_animated(Fore.BLUE +
                            f"AI User:\n\n{user_response.msg.content}\n")

        # Print output from the assistant, including any function
        # execution information
        print_text_animated(Fore.GREEN + "AI Assistant:")
        called_functions: List[
            FunctionCallingRecord] = assistant_response.info[
                'called_functions']
        for func_record in called_functions:
            print_text_animated(f"{func_record}")
        print_text_animated(f"{assistant_response.msg.content}\n")

        if "CAMEL_TASK_DONE" in user_response.msg.content:
            break

        input_assistant_msg = assistant_response.msg
