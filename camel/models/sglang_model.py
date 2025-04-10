# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
import logging
import os
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Type, Union

from openai import AsyncOpenAI, AsyncStream, OpenAI, Stream
from pydantic import BaseModel

from camel.configs import SGLANG_API_PARAMS, SGLangConfig
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
)
from camel.utils import BaseTokenCounter, OpenAITokenCounter


class SGLangModel(BaseModelBackend):
    r"""SGLang service interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`SGLangConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the model service. SGLang doesn't need API key, it would be ignored
            if set. (default: :obj:`None`)
        url (Optional[str], optional): The url to the model service. If not
            provided, :obj:`"http://127.0.0.1:30000/v1"` will be used.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter(
            ModelType.GPT_4O_MINI)` will be used.
            (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)

    Reference: https://sgl-project.github.io/backend/openai_api_completions.html
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = SGLangConfig().as_dict()

        self.server_process = None
        self.last_run_time: Optional[float] = (
            None  # Will be set when the server starts
        )
        self._lock = threading.Lock()
        self._inactivity_thread: Optional[threading.Thread] = None

        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter, timeout
        )

        self._client = None

        if self._url:
            # Initialize the client if an existing URL is provided
            self._client = OpenAI(
                timeout=self._timeout,
                max_retries=3,
                api_key="Set-but-ignored",  # required but ignored
                base_url=self._url,
            )
            self._async_client = AsyncOpenAI(
                timeout=self._timeout,
                max_retries=3,
                api_key="Set-but-ignored",  # required but ignored
                base_url=self._url,
            )

    def _start_server(self) -> None:
        try:
            if not self._url:
                tool_call_flag = self.model_config_dict.get("tools")
                tool_call_arg = (
                    f"--tool-call-parser {self._api_key} "
                    if tool_call_flag
                    else ""
                )
                cmd = (
                    f"python -m sglang.launch_server "
                    f"--model-path {self.model_type} "
                    f"{tool_call_arg}"
                    f"--port 30000 "
                    f"--host 0.0.0.0"
                )

                server_process = _execute_shell_command(cmd)
                _wait_for_server("http://localhost:30000")
                self._url = "http://127.0.0.1:30000/v1"
                self.server_process = server_process  # type: ignore[assignment]
                # Start the inactivity monitor in a background thread
                self._inactivity_thread = threading.Thread(
                    target=self._monitor_inactivity, daemon=True
                )
                self._inactivity_thread.start()
            self.last_run_time = time.time()
            # Initialize the client after the server starts
            self._client = OpenAI(
                timeout=self._timeout,
                max_retries=3,
                api_key="Set-but-ignored",  # required but ignored
                base_url=self._url,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start SGLang server: {e}") from e

    def _ensure_server_running(self) -> None:
        r"""Ensures that the server is running. If not, starts the server."""
        with self._lock:
            if self.server_process is None:
                self._start_server()

    def _monitor_inactivity(self):
        r"""Monitor whether the server process has been inactive for over 10
        minutes.
        """
        while True:
            # Check every 10 seconds
            time.sleep(10)
            # Over 10 minutes
            with self._lock:
                # Over 10 minutes
                if self.last_run_time and (
                    time.time() - self.last_run_time > 600
                ):
                    if self.server_process:
                        _terminate_process(self.server_process)
                        self.server_process = None
                        self._client = None  # Invalidate the client
                        logging.info(
                            "Server process terminated due to inactivity."
                        )
                    break

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        return self._token_counter

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to SGLang API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to OpenAI API.
        """
        for param in self.model_config_dict:
            if param not in SGLANG_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into SGLang model backend."
                )

    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Runs inference of OpenAI chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `AsyncStream[ChatCompletionChunk]` in the stream mode.
        """

        # Ensure server is running
        self._ensure_server_running()

        with self._lock:
            # Update last run time
            self.last_run_time = time.time()

        if self._client is None:
            raise RuntimeError(
                "Client is not initialized. Ensure the server is running."
            )

        response = await self._async_client.chat.completions.create(
            messages=messages,
            model=self.model_type,
            **self.model_config_dict,
        )

        return response

    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of OpenAI chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
        """

        # Ensure server is running
        self._ensure_server_running()

        with self._lock:
            # Update last run time
            self.last_run_time = time.time()

        if self._client is None:
            raise RuntimeError(
                "Client is not initialized. Ensure the server is running."
            )

        response = self._client.chat.completions.create(
            messages=messages,
            model=self.model_type,
            **self.model_config_dict,
        )

        return response

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)

    def __del__(self):
        r"""Properly clean up resources when the model is destroyed."""
        self.cleanup()

    def cleanup(self):
        r"""Terminate the server process and clean up resources."""
        with self._lock:
            if self.server_process:
                _terminate_process(self.server_process)
                self.server_process = None
                self._client = None
                logging.info("Server process terminated during cleanup.")


# Below are helper functions from sglang.utils
def _terminate_process(process):
    _kill_process_tree(process.pid)


def _kill_process_tree(
    parent_pid, include_parent: bool = True, skip_pid: Optional[int] = None
):
    r"""Kill the process and all its child processes."""
    import os
    import signal

    import psutil

    if parent_pid is None:
        parent_pid = os.getpid()
        include_parent = False

    try:
        itself = psutil.Process(parent_pid)
    except psutil.NoSuchProcess:
        return

    children = itself.children(recursive=True)
    for child in children:
        if child.pid == skip_pid:
            continue
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass

    if include_parent:
        try:
            itself.kill()

            # Sometime processes cannot be killed with SIGKILL
            # so we send an additional signal to kill them.
            if hasattr(signal, "SIGQUIT"):
                itself.send_signal(signal.SIGQUIT)
            else:
                itself.send_signal(signal.SIGTERM)
        except psutil.NoSuchProcess:
            pass


def _execute_shell_command(command: str) -> subprocess.Popen:
    r"""Execute a shell command and return the process handle

    Args:
        command: Shell command as a string (can include \\ line continuations)
    Returns:
        subprocess.Popen: Process handle
    """
    import subprocess

    # Replace \ newline with space and split
    command = command.replace("\\\n", " ").replace("\\", " ")
    parts = command.split()

    return subprocess.Popen(parts, text=True, stderr=subprocess.STDOUT)


def _wait_for_server(base_url: str, timeout: Optional[int] = 30) -> None:
    r"""Wait for the server to be ready by polling the /v1/models endpoint.

    Args:
        base_url (str): The base URL of the server
        timeout (Optional[int]): Maximum time to wait in seconds.
            (default: :obj:`30`)
    """
    import requests

    # Set a default value if timeout is None
    actual_timeout = 30 if timeout is None else timeout

    start_time = time.time()
    while True:
        try:
            response = requests.get(
                f"{base_url}/v1/models",
                headers={"Authorization": "Bearer None"},
                timeout=5,  # Add a timeout for the request itself
            )
            if response.status_code == 200:
                time.sleep(5)
                print(
                    """\n
                    NOTE: Typically, the server runs in a separate terminal.
                    In this notebook, we run the server and notebook code 
                    together, so their outputs are combined.
                    To improve clarity, the server logs are displayed in the 
                    original black color, while the notebook outputs are 
                    highlighted in blue.
                    """
                )
                break

            if time.time() - start_time > actual_timeout:
                raise TimeoutError(
                    f"Server did not become ready within "
                    f"{actual_timeout} seconds"
                )
        except (requests.exceptions.RequestException, TimeoutError) as e:
            if time.time() - start_time > actual_timeout:
                raise TimeoutError(
                    f"Server did not become ready within "
                    f"{actual_timeout} seconds: {e}"
                )
            time.sleep(1)
