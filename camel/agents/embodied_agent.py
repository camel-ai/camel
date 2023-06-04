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
from typing import Any, Dict, List, Optional, Tuple

from colorama import Fore

from camel.agents import ChatAgent, HuggingFaceToolAgent, ToolAgent
from camel.messages import ChatMessage, SystemMessage
from camel.typing import ModelType
from camel.utils import print_text_animated


class EmbodiedAgent(ChatAgent):
    r"""Class for managing conversations of CAMEL Embodied Agents.

    Args:
        system_message (SystemMessage): The system message for the chat agent.
        model (ModelType, optional): The LLM model to use for generating
            responses. (default :obj:`ModelType.GPT_4`)
        model_config (Any, optional): Configuration options for the LLM model.
            (default: :obj:`None`)
        message_window_size (int, optional): The maximum number of previous
            messages to include in the context window. If `None`, no windowing
            is performed. (default: :obj:`None`)
        action_space (List[Any], optional): The action space for the embodied
            agent. (default: :obj:`None`)
        verbose (bool, optional): Whether to print the critic's messages.
        logger_color (Any): The color of the logger displayed to the user.
            (default: :obj:`Fore.MAGENTA`)
    """

    def __init__(
        self,
        system_message: SystemMessage,
        model: ModelType = ModelType.GPT_4,
        model_config: Optional[Any] = None,
        message_window_size: Optional[int] = None,
        action_space: Optional[List[ToolAgent]] = None,
        verbose: bool = False,
        logger_color: Any = Fore.MAGENTA,
    ) -> None:
        default_action_space = [
            HuggingFaceToolAgent('hugging_face_tool_agent', model=model.value),
        ]
        self.action_space = action_space or default_action_space
        action_space_prompt = self.get_action_space_prompt()
        system_message.content = system_message.content.format(
            action_space=action_space_prompt)
        self.verbose = verbose
        self.logger_color = logger_color
        super().__init__(
            system_message=system_message,
            model=model,
            model_config=model_config,
            message_window_size=message_window_size,
        )

    def get_action_space_prompt(self) -> str:
        r"""Returns the action space prompt.

        Returns:
            str: The action space prompt.
        """
        return "\n".join([
            f"*** {action.name} ***:\n {action.description}"
            for action in self.action_space
        ])

    @staticmethod
    def execute_code(code_string: str, global_vars: Dict = None) -> str:
        r"""Executes the given code string.

        Args:
            code_string (str): The code string to execute.
            global_vars (Dict, optional): The global variables to use during
                code execution. (default: :obj:`None`)

        Returns:
            str: The execution results.
        """
        try:
            # Execute the code string
            import io
            import sys
            output_str = io.StringIO()
            sys.stdout = output_str

            global_vars = global_vars or globals()
            local_vars = {}
            exec(
                code_string,
                global_vars,
                local_vars,
            )
            sys.stdout = sys.__stdout__
            output_str.seek(0)

            # If there was no error, return the output
            return (f"- Python standard output:\n{output_str.read()}\n"
                    f"- Local variables:\n{str(local_vars)}")
        except Exception:
            import traceback
            traceback_str = traceback.format_exc()
            sys.stdout = sys.__stdout__
            # If there was an error, return the error message
            return f"Traceback:\n{traceback_str}"

    @staticmethod
    def get_explanation_and_code(
            text_prompt: str) -> Tuple[str, Optional[str]]:
        r"""Extracts the explanation and code from the text prompt.

        Args:
            text_prompt (str): The text prompt containing the explanation and
                code.

        Returns:
            Tuple[str, Optional[str]]: The extracted explanation and code.
        """
        lines = text_prompt.split("\n")
        idx = 0
        while idx < len(lines) and not lines[idx].lstrip().startswith("```"):
            idx += 1
        explanation = "\n".join(lines[:idx]).strip()
        if idx == len(lines):
            return explanation, None

        idx += 1
        start_idx = idx
        while not lines[idx].lstrip().startswith("```"):
            idx += 1
        code = "\n".join(lines[start_idx:idx]).strip()

        return explanation, code

    def step(
        self,
        input_message: ChatMessage,
    ) -> Tuple[ChatMessage, bool, Dict[str, Any]]:
        r"""Performs a step in the conversation.

        Args:
            input_message (ChatMessage): The input message.

        Returns:
            Tuple[ChatMessage, bool, Dict[str, Any]]: A tuple
                containing the output messages, termination status, and
                additional information.
        """
        output_messages, terminated, info = super().step(input_message)

        if output_messages is None:
            raise RuntimeError("Got None output messages.")
        if terminated:
            raise RuntimeError(f"{self.__class__.__name__} step failed.")

        # NOTE: Only single output messages are supported
        output_message = output_messages[0]
        explanation, code = self.get_explanation_and_code(
            output_message.content)
        if self.verbose:
            print_text_animated(self.logger_color +
                                f"> Explanation:\n{explanation}")
            print_text_animated(self.logger_color + f"> Code:\n{code}")

        if code is not None:
            global_vars = {action.name: action for action in self.action_space}
            executed_results = self.execute_code(code, global_vars)
            output_message.content += (
                f"\n> Executed Results:\n{executed_results}")

        # TODO: Handle errors
        input_message.content += (
            f"\n> Embodied Actions:\n{output_message.content}")
        return input_message, terminated, info
