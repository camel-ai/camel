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


def text_extract_from_web(url: str) -> str:
    r"""Get the text information from given url.

    Args:
        url (str): The website you want to search.

    Returns:
        str: All texts extract from the web.
    """
    try:
        import requests
        from newspaper import Article

        # Request the target page
        article = Article(url)
        article.download()
        article.parse()
        text = article.text

    except requests.RequestException as e:
        text = f"Can't access {url}, error: {e}"

    except Exception as e:
        text = f"Can't extract text from {url}, error: {e}"

    return text


# Split a text into smaller chunks of size n
def create_chunks(text: str, n: int) -> List[str]:
    r"""Returns successive n-sized chunks from provided text."

    Args:
        text (str): The text to be split.
        n (int): The max length of a single chunk.

    Returns:
        List[str]: A list of split texts.
    """

    chunks = []
    i = 0
    while i < len(text):
        # Find the nearest end of sentence within a range of 0.5 * n
        # and 1.5 * n tokens
        j = min(i + int(1.2 * n), len(text))
        while j > i + int(0.8 * n):
            # Decode the tokens and check for full stop or newline
            chunk = text[i:j]
            if chunk.endswith(".") or chunk.endswith("\n"):
                break
            j -= 1
        # If no end of sentence found, use n tokens as the chunk size
        if j == i + int(0.8 * n):
            j = min(i + n, len(text))
        chunks.append(text[i:j])
        i = j
    return chunks


def prompt_single_step_agent(prompt: str) -> str:
    """Prompt a single-step agent to summarize texts or answer a question."""

    from camel.agents import ChatAgent
    from camel.messages import BaseMessage

    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful assistant.",
    )
    agent = ChatAgent(assistant_sys_msg)
    agent.reset()

    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content=prompt,
    )
    assistant_response = agent.step(user_msg)
    if assistant_response.msgs is not None:
        return assistant_response.msg.content
    return ""


def summarize_text(text: str, query: str) -> str:
    r"""Summarize the information from the text, base on the query if query is
        given.

    Args:
        text (str): Text to summarize.
        query (str): What information you want.

    Returns:
        str: Strings with information.
    """
    from camel.prompts import TextPrompt

    summary_prompt = TextPrompt(
        '''Gather information from this text that relative to the question, but 
do not directly answer the question.\nquestion: {query}\ntext '''
    )
    summary_prompt = summary_prompt.format(query=query)
    # Max length of each chunk
    max_len = 3000
    results = ""
    chunks = create_chunks(text, max_len)
    # Summarize
    for i, chunk in enumerate(chunks, start=1):
        prompt = summary_prompt + str(i) + ": " + chunk
        result = prompt_single_step_agent(prompt)
        results += result + "\n"

    # Final summarise
    final_prompt = TextPrompt(
        '''Here are some summarized texts which split from one text. Using the information to answer the question.
If can't find the answer, you must answer "I can not find the answer to the query" and explain why.\n
Query:\n{query}.\n\nText:\n'''
    )
    final_prompt = final_prompt.format(query=query)
    prompt = final_prompt + results

    response = prompt_single_step_agent(prompt)

    return response


def continue_search(query: str, answer: str) -> bool:
    r"""Ask LLM whether to continue search or not.

    Args:
        query (str): Question you want to be answered.
        answer (str): Answer to the query.

    Returns:
        bool: True if the user want to continue search, False otherwise.
    """
    from camel.prompts import TextPrompt

    prompt = TextPrompt(
        "Do you think the ANSWER can answer the QUERY? "
        "Use only 'yes' or 'no' to answer.\n"
        "===== QUERY =====\n{query}\n\n"
        "===== ANSWER =====\n{answer}"
    )
    prompt = prompt.format(query=query, answer=answer)
    reply = prompt_single_step_agent(prompt)
    if "yes" in str(reply).lower():
        return False
    return True
