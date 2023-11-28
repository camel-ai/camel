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
import os
import re
import socket
import time
import zipfile
from functools import wraps
from inspect import Parameter, signature
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    TypeVar,
    cast,
)
from urllib.parse import urlparse

import requests
from docstring_parser import parse
from pydantic import create_model
from pydantic._internal import _typing_extra
from pydantic.alias_generators import to_pascal

from camel.types import TaskType

F = TypeVar('F', bound=Callable[..., Any])


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


def get_openai_function_schema(func: Callable) -> Dict[str, any]:

    def _remove_a_key(d, remove_key) -> None:
        r"""Remove a key from a dictionary recursively"""
        if isinstance(d, dict):
            for key in list(d.keys()):
                if key == remove_key and "type" in d.keys():
                    del d[key]
                else:
                    _remove_a_key(d[key], remove_key)

    parameters: Mapping[str, Parameter] = signature(func).parameters
    raw_function = func
    arg_mapping: Dict[int, str] = {}
    positional_only_args: Set[str] = set()
    type_hints = _typing_extra.get_type_hints(func, include_extras=True)
    fields: Dict[str, Tuple[Any, Any]] = {}
    for i, (name, p) in enumerate(parameters.items()):
        if p.annotation is p.empty:
            annotation = Any
        else:
            annotation = type_hints[name]

        default = ... if p.default is p.empty else p.default
        if p.kind == Parameter.POSITIONAL_ONLY:
            arg_mapping[i] = name
            fields[name] = annotation, default
            positional_only_args.add(name)
        elif p.kind == Parameter.POSITIONAL_OR_KEYWORD:
            arg_mapping[i] = name
            fields[name] = annotation, default

        elif p.kind == Parameter.KEYWORD_ONLY:
            fields[name] = annotation, default
        elif p.kind == Parameter.VAR_POSITIONAL:
            fields[name] = Tuple[annotation, ...], None
        else:
            assert p.kind == Parameter.VAR_KEYWORD, p.kind
            fields[name] = Dict[str, annotation], None
    model = create_model(to_pascal(raw_function.__name__), **fields)

    parameters = model.model_json_schema()

    parameters["properties"] = {
        k: v
        for k, v in parameters["properties"].items()
        if k not in ("args", "kwargs")
    }
    _remove_a_key(parameters, "additionalProperties")
    _remove_a_key(parameters, "title")

    docstring = parse(func.__doc__ or "")
    for param in docstring.params:
        if ((name := param.arg_name) in parameters["properties"]
                and (description := param.description)):
            parameters["properties"][name]["description"] = description

    openai_function_schema = {
        "name":
        func.__name__,
        "description":
        (docstring.short_description if docstring.short_description else "") +
        (docstring.long_description if docstring.long_description else ""),
        "parameters":
        parameters,
    }
    return openai_function_schema


def get_openai_tool_schema(func: Callable) -> Dict[str, Any]:
    openai_function_schema = get_openai_function_schema(func)
    openai_tool_schema = {
        "type": "function",
        "function": openai_function_schema
    }
    return openai_tool_schema
