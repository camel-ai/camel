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
from typing import Any, List, Literal, Optional

from colorama import Fore

from camel.agents.chat_agent import ChatAgent
from camel.agents.tool_agents.base import BaseToolAgent
from camel.interpreters import (
    BaseInterpreter,
    DockerInterpreter,
    E2BInterpreter,
    InternalPythonInterpreter,
    JupyterKernelInterpreter,
    SubprocessInterpreter,
)
from camel.messages import BaseMessage
from camel.models import BaseModelBackend
from camel.responses import ChatAgentResponse
from camel.runtime import LLMGuardRuntime
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.utils import print_text_animated

# AgentOps decorator setting
try:
    import os

    if os.getenv("AGENTOPS_API_KEY") is not None:
        from agentops import track_agent
    else:
        raise ImportError
except (ImportError, AttributeError):
    from camel.utils import track_agent


@track_agent(name="EmbodiedAgent")
class EmbodiedAgent(ChatAgent):
    r"""Class for managing conversations of CAMEL Embodied Agents.

    Args:
        system_message (BaseMessage): The system message for the chat agent.
        model (BaseModelBackend, optional): The model backend to use for
            generating responses. (default: :obj:`OpenAIModel` with
            `GPT_4O_MINI`)
        message_window_size (int, optional): The maximum number of previous
            messages to include in the context window. If `None`, no windowing
            is performed. (default: :obj:`None`)
        tool_agents (List[BaseToolAgent], optional): The tools agents to use in
            the embodied agent. (default: :obj:`None`)
        code_interpreter (BaseInterpreter, optional): The code interpreter to
            execute codes. If `code_interpreter` and `tool_agent` are both
            `None`, default to `SubProcessInterpreter`. If `code_interpreter`
            is `None` and `tool_agents` is not `None`, default to
            `InternalPythonInterpreter`.  (default: :obj:`None`)
        verbose (bool, optional): Whether to print the critic's messages.
        logger_color (Any): The color of the logger displayed to the user.
            (default: :obj:`Fore.MAGENTA`)
        use_llm_guard (bool, optional): Whether to use LLMGuardRuntime for
            secure code execution. (default: :obj:`True`)
        risk_threshold (int, optional): Risk threshold for code execution
            when using LLMGuardRuntime. (default: :obj:`2`)
        llm_guard_model (BaseModelBackend, optional): The model backend to use for
            LLM guard security checks when use_llm_guard is True.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        system_message: BaseMessage,
        model: Optional[BaseModelBackend] = None,
        message_window_size: Optional[int] = None,
        tool_agents: Optional[List[BaseToolAgent]] = None,
        code_interpreter: Optional[BaseInterpreter] = None,
        verbose: bool = False,
        logger_color: Any = Fore.MAGENTA,
        use_llm_guard: bool = True,
        llm_guard_model: Optional[BaseModelBackend] = None,
        risk_threshold: int = 2,
    ) -> None:
        self.tool_agents = tool_agents
        self.use_llm_guard = use_llm_guard
        self.risk_threshold = risk_threshold

        # Fallback interpreter usage
        self.code_interpreter: BaseInterpreter
        if code_interpreter is not None:
            self.code_interpreter = code_interpreter
        elif self.tool_agents:
            self.code_interpreter = InternalPythonInterpreter()
        else:
            self.code_interpreter = SubprocessInterpreter()

        # Set up secure code execution
        if use_llm_guard:
            self._setup_secure_code_execution(
                code_interpreter, verbose, llm_guard_model
            )

        if self.tool_agents:
            system_message = self._set_tool_agents(system_message)
        self.verbose = verbose
        self.logger_color = logger_color
        super().__init__(
            system_message=system_message,
            model=model,
            message_window_size=message_window_size,
        )

    def _setup_secure_code_execution(
        self,
        code_interpreter: Optional[BaseInterpreter],
        verbose: bool,
        llm_guard_model: Optional[BaseModelBackend] = None,
    ) -> None:
        """Set up secure code execution using CodeExecutionToolkit with LLMGuardRuntime."""
        # Determine sandbox type based on interpreter preference
        sandbox: Literal[
            'internal_python', 'jupyter', 'docker', 'subprocess', 'e2b'
        ]
        if code_interpreter is not None:
            if isinstance(code_interpreter, InternalPythonInterpreter):
                sandbox = "internal_python"
            elif isinstance(code_interpreter, SubprocessInterpreter):
                sandbox = "subprocess"
            elif isinstance(code_interpreter, DockerInterpreter):
                sandbox = "docker"
            elif isinstance(code_interpreter, E2BInterpreter):
                sandbox = "e2b"
            elif isinstance(code_interpreter, JupyterKernelInterpreter):
                sandbox = "jupyter"
            else:
                sandbox = "subprocess"
        elif self.tool_agents:
            sandbox = "internal_python"
        else:
            sandbox = "subprocess"

        # Create CodeExecutionToolkit with proper type casting
        self.code_execution_toolkit = CodeExecutionToolkit(
            sandbox=sandbox,
            verbose=verbose,
            require_confirm=False,  # LLMGuardRuntime handles security
        )

        # Set up LLMGuardRuntime with the toolkit
        if llm_guard_model is not None:
            self.llm_guard_runtime = LLMGuardRuntime(
                verbose=verbose, model=llm_guard_model
            )
        else:
            self.llm_guard_runtime = LLMGuardRuntime(verbose=verbose)

        self.llm_guard_runtime.add(
            self.code_execution_toolkit.get_tools(),
            threshold=self.risk_threshold,
        )

        # Get the secured tools
        self.secure_tools = self.llm_guard_runtime.get_tools()
        self.execute_code_func = None
        for tool in self.secure_tools:
            if tool.get_function_name() == "execute_code":
                self.execute_code_func = tool.func
                break

    def _execute_code_securely(
        self, code: str, code_type: str = "python"
    ) -> str:
        """Execute code using secure LLMGuardRuntime."""
        if self.use_llm_guard and self.execute_code_func:
            try:
                result = self.execute_code_func(code)
                # Extract just the execution result from the formatted output
                if (
                    isinstance(result, str)
                    and "> Executed Results:\n" in result
                ):
                    return result.split("> Executed Results:\n", 1)[1]
                return str(result)
            except Exception as e:
                return f"Code execution failed with security check: {e}"
        else:
            # Fallback to direct interpreter
            return self.code_interpreter.run(code, code_type)

    def _set_tool_agents(self, system_message: BaseMessage) -> BaseMessage:
        action_space_prompt = self._get_tool_agents_prompt()
        result_message = system_message.create_new_instance(
            content=system_message.content.format(
                action_space=action_space_prompt
            )
        )
        if self.tool_agents is not None:
            self.code_interpreter.update_action_space(
                {tool.name: tool for tool in self.tool_agents}
            )
        return result_message

    def _get_tool_agents_prompt(self) -> str:
        r"""Returns the action space prompt.

        Returns:
            str: The action space prompt.
        """
        if self.tool_agents is not None:
            return "\n".join(
                [
                    f"*** {tool.name} ***:\n {tool.description}"
                    for tool in self.tool_agents
                ]
            )
        else:
            return ""

    def get_tool_agent_names(self) -> List[str]:
        r"""Returns the names of tool agents.

        Returns:
            List[str]: The names of tool agents.
        """
        if self.tool_agents is not None:
            return [tool.name for tool in self.tool_agents]
        else:
            return []

    # ruff: noqa: E501
    def step(self, input_message: BaseMessage) -> ChatAgentResponse:  # type: ignore[override]
        r"""Performs a step in the conversation.

        Args:
            input_message (BaseMessage): The input message.

        Returns:
            ChatAgentResponse: A struct containing the output messages,
                a boolean indicating whether the chat session has terminated,
                and information about the chat session.
        """
        response = super().step(input_message)

        if response.msgs is None or len(response.msgs) == 0:
            raise RuntimeError("Got None output messages.")
        if response.terminated:
            raise RuntimeError(f"{self.__class__.__name__} step failed.")

        # NOTE: Only single output messages are supported
        explanations, codes = response.msg.extract_text_and_code_prompts()

        if self.verbose:
            for explanation, code in zip(explanations, codes):
                print_text_animated(
                    self.logger_color + f"> Explanation:\n{explanation}"
                )
                print_text_animated(self.logger_color + f"> Code:\n{code}")

            if len(explanations) > len(codes):
                print_text_animated(
                    self.logger_color + f"> Explanation:\n{explanations[-1]}"
                )

        content = response.msg.content

        if codes is not None:
            try:
                content = "\n> Executed Results:\n"
                for block_idx, code in enumerate(codes):
                    executed_output = self._execute_code_securely(
                        code, code.code_type
                    )
                    content += (
                        f"Executing code block {block_idx}: {{\n"
                        + executed_output
                        + "}\n"
                    )
            except InterruptedError as e:
                content = (
                    f"\n> Running code fail: {e}\n"
                    "Please regenerate the code."
                )

        # TODO: Handle errors
        content = input_message.content + f"\n> Embodied Actions:\n{content}"
        message = BaseMessage(
            input_message.role_name,
            input_message.role_type,
            input_message.meta_dict,
            content,
        )
        return ChatAgentResponse(
            msgs=[message],
            terminated=response.terminated,
            info=response.info,
        )
