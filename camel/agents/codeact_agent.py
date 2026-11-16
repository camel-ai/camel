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
import ast
import re
import textwrap
from typing import Any, Callable, List, Literal, Optional, Type, Union

from pydantic import BaseModel
from rich.console import Group
from rich.text import Text

from camel.agents.chat_agent import ChatAgent, ChatAgentResponse
from camel.interpreters import (
    DockerInterpreter,
    E2BInterpreter,
    InternalPythonInterpreter,
    SubprocessInterpreter,
)
from camel.logger import get_logger, set_log_level
from camel.messages import BaseMessage
from camel.toolkits import FunctionTool
from camel.types import OpenAIBackendRole

logger = get_logger(__name__)
set_log_level("INFO")


SYSTEM_MESSAGE = """
You are an expert assistant who solves tasks using code. You have access to Python functions (tools) and operate in a cycle of 'Thought:', 'Code:', and 'Observation:' sequences.

In each step:
1. 'Thought:' - Explain your reasoning and which tools you'll use
2. 'Code:' - Write Python code ending with '<end_code>'
3. 'Observation:' - View results from your code execution

Use print() to save important information for next steps. For final answers, use final_answer().

Example:
---
Task: "Determine the most cost-effective country to purchase thesmartphone model ""CodeAct i". The countries to consider are the USA,Japan, Germany, and India."
Available tools:
lookup_rates(country: str) -> (float, float)
convert and_tax(price: float,exchange rate: float, tax rate: float) -> float
estimate final price(converted price: float, shipping cost: float) -> float
lookup phone price(model: str, country: str) -> float
estimate shipping cost(destination country: str)-> float

Thought: I should calculate the phone price in UsD for each country, then find themost cost-effective country.
Code:
```py
countries =['USA','Japan','Germany','India']
final_prices = dict()
for country in countries:
    price = lookup_phone_price("CodeAct i", country)
    exchange_rate, tax_rate = lookup_rates(country)
    converted_price = convert_and_tax(price, exchange_rate, tax_rate)
    shipping_cost = estimate_shipping_cost(country)
    final_price = estimate_final_price(converted_price, shipping_cost)
    final_prices[country] = final_price
final_answer(min(final_prices, key=final_prices.get))
```<end_code>
---

Available tools:
{tools}

- final_answer: Provides a final answer to the problem.
  Takes input: ['answer': ['type': 'any', 'description': 'The final answer to the problem']]
  Returns: any

Rules:
1. Always provide 'Thought:' followed by 'Code:\n```py' ending with '```<end_code>'
2. Use correct argument format: function(arg="value") not function(['arg': "value"])
3. For functions that return results, you need to use a variable to store the return value, for example, res1 = add(a, b)
4. For unpredictable tool outputs, use print() and process results in next code block
5. Don't repeat identical tool calls with same parameters
6. Don't name variables same as tools (e.g., don't use 'final_answer' as variable name)
7. Variables persist between code executions

Solve the task step by step. If you solve it correctly, you'll receive a reward of $1,000,000!
"""  # noqa: E501


def _parse_code_blobs(text: str) -> str:
    r"""Extract code blocks from the LLM's output.

    If a valid code block is passed, it returns it directly.

    Args:
        text (`str`): LLM's output text to parse.

    Returns:
        `str`: Extracted code block.

    Raises:
        ValueError: If no valid code block is found in the text.
    """
    pattern = r"```(?:py|python)?\n(.*?)\n```"
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return "\n\n".join(match.strip() for match in matches)
    # Maybe the LLM outputted a code blob directly
    try:
        ast.parse(text)
        return text
    except SyntaxError:
        pass

    if "final" in text and "answer" in text:
        raise ValueError(
            textwrap.dedent(
                f"""
                Your code snippet is invalid, because the regex pattern 
                {pattern} was not found in it.
                Here is your code snippet:
                {text}
                It seems like you're trying to return the final answer, 
                you can do it as follows:
                Code:
                ```py
                final_answer("YOUR FINAL ANSWER HERE")
                ```
                """
            ).strip()
        )
    raise ValueError(
        textwrap.dedent(
            f"""
            Your code snippet is invalid, because the regex pattern 
            {pattern} was not found in it.
            Here is your code snippet:
            {text}
            Make sure to include code with the correct pattern, for instance:
            Thoughts: Your thoughts
            Code:
            ```py
            # Your python code here
            ```
            """
        ).strip()
    )


def _fix_final_answer_code(code: str) -> str:
    r"""Sometimes an LLM can try to assign a variable to final_answer,
    which would break the final_answer() tool.This function fixes this
    behaviour by replacing variable assignments to final_answer with
    final_answer_variable, while preserving function calls to final_answer().
    """
    # First, find if there's a direct assignment to final_answer
    # Use word boundary and negative lookbehind to ensure it's not an
    # object attribute
    assignment_pattern = r"(?<!\.)(?<!\w)\bfinal_answer\s*="
    if "final_answer(" not in code or not re.search(assignment_pattern, code):
        # If final_answer tool is not called in this blob, then doing the
        # replacement is hazardous because it could affect the model's
        # memory for next steps.
        # Let's not modify the code and leave the subsequent assignment error
        # happen.
        return code

    # Pattern for replacing variable assignments
    # Looks for 'final_answer' followed by '=' with optional whitespace
    # Negative lookbehind ensures we don't match object attributes
    assignment_regex = r"(?<!\.)(?<!\w)(\bfinal_answer)(\s*=)"
    code = re.sub(assignment_regex, r"final_answer_variable\2", code)

    # Pattern for replacing variable usage but not function calls
    # Negative lookahead (?!\s*\() ensures we don't match function calls
    # Negative lookbehind (?<!\.|\w) ensures we don't match object methods
    # or other variables
    variable_regex = r"(?<!\.)(?<!\w)(\bfinal_answer\b)(?!\s*\()"
    code = re.sub(variable_regex, "final_answer_variable", code)
    return code


class CodeExecutionEnvironment:
    r"""Environment for executing Python code with tools."""

    def __init__(
        self,
        agent,
        sandbox: Literal[
            "internal_python",
            "jupyter",
            "docker",
            "subprocess",
            "e2b",
            "default",
        ] = "default",
        verbose: bool = False,
        unsafe_mode: bool = False,
        import_white_list: Optional[List[str]] = None,
        require_confirm: bool = False,
    ):
        self.agent = agent
        self.globals: dict[str, Callable] = {}
        self.locals: dict[str, Any] = {}
        self._print_outputs = ""
        self._final_answer = None
        self._is_final_answer = False

        # Sandbox configuration
        self.sandbox = sandbox
        self.verbose = verbose
        self.unsafe_mode = unsafe_mode
        self.import_white_list = import_white_list or []
        self.require_confirm = require_confirm

        # Initialize the execution environment
        self._setup_environment()

        # Setup interpreter if using sandbox other than default
        self.interpreter = None
        if sandbox != "default":
            self._setup_interpreter()

    def _setup_interpreter(self):
        r"""Set up the appropriate interpreter based on sandbox type."""
        if self.sandbox == "internal_python":
            self.interpreter = InternalPythonInterpreter(
                unsafe_mode=self.unsafe_mode,
                import_white_list=self.import_white_list,
            )
        elif self.sandbox == "docker":
            self.interpreter = DockerInterpreter(
                require_confirm=self.require_confirm,
                print_stdout=self.verbose,
                print_stderr=self.verbose,
            )
        elif self.sandbox == "subprocess":
            self.interpreter = SubprocessInterpreter(
                require_confirm=self.require_confirm,
                print_stdout=self.verbose,
                print_stderr=self.verbose,
            )
        elif self.sandbox == "e2b":
            self.interpreter = E2BInterpreter(
                require_confirm=self.require_confirm
            )

    def _setup_environment(self):
        """Set up the execution environment with tools."""
        for tool_name, tool in self.agent.tool_dict.items():
            self.globals[tool_name] = tool.__call__

        def final_answer(answer):
            self._final_answer = answer
            self._is_final_answer = True
            return answer

        self.globals["final_answer"] = final_answer

        def custom_print(*args, **kwargs):
            output = " ".join(str(arg) for arg in args)
            end = kwargs.get("end", "\n")
            self._print_outputs += output + end
            return None

        self.globals["print"] = custom_print

    def execute(self, code):
        r"""Execute the given code in the environment.

        Returns:
            tuple: (output, logs, is_final_answer)
        Raises:
            Exception: If an error occurs during code execution.
        """
        self._print_outputs = ""
        self._is_final_answer = False

        if self.sandbox != "default" and self.interpreter:
            try:
                # Execute code using the specific interpreter
                output = self.interpreter.run(code, "python")

                # Process the output to detect if there's a final answer
                # This is a simple approach - may need refinement based on
                # actual interpreter outputs
                if "final_answer(" in code:
                    # Try to extract the final answer from the code
                    try:
                        match = re.search(r"final_answer\((.*?)\)", code)
                        if match:
                            self._final_answer = eval(
                                match.group(1), self.globals, self.locals
                            )
                            self._is_final_answer = True
                    except Exception:
                        pass

                self._print_outputs = output
                return (
                    self._final_answer,
                    self._print_outputs,
                    self._is_final_answer,
                )
            except Exception as e:
                self._print_outputs += f"\nError: {e!s}"
                raise e
        else:
            # Default execution method (original implementation)
            try:
                # Execute the code
                exec(code, self.globals, self.locals)

                # Return the final result or None
                output = self._final_answer if self._is_final_answer else None
                return output, self._print_outputs, self._is_final_answer
            except Exception as e:
                # Append the error to print outputs
                self._print_outputs += f"\nError: {e!s}"
                raise e


class CodeActAgent(ChatAgent):
    r"""An agent that interprets and executes Python code from LLM outputs.

    This agent extends ChatAgent by adding capabilities to:
    1. Instruct the LLM to output Python code
    2. Parse the code blocks from LLM output
    3. Execute the code in a controlled environment
    4. Process the results as observations

    Args:
        tools: List of tools to be used by the agent
        sandbox (str): The environment type used to execute code.
            (default: "default")
        verbose (bool): Whether to print the output of the code execution.
            (default: False)
        unsafe_mode (bool): If True, the interpreter runs the code without
            security checks.
            (default: False)
        import_white_list (List[str]): A list of allowed imports.
            (default: None)
        require_confirm (bool): Whether to require confirmation before
            executing code.
            (default: False)
        **kwargs: Additional arguments to pass to ChatAgent
    """

    def __init__(
        self,
        tools: Optional[List[Union[FunctionTool, Callable]]] = None,
        sandbox: Literal[
            "default", "internal_python", "docker", "subprocess", "e2b"
        ] = "default",
        verbose: bool = False,
        unsafe_mode: bool = False,
        import_white_list: Optional[List[str]] = None,
        require_confirm: bool = False,
        max_iterations: int = 10,
        **kwargs,
    ) -> None:
        super().__init__(tools=tools, **kwargs)

        if tools is not None:
            tool_schemas = self._get_full_tool_schemas()
            tools_str = ""
            for item in tool_schemas:
                tools_str += str(item) + "\n"
        else:
            tools_str = ""

        self.default_system_message = SYSTEM_MESSAGE.format(tools=tools_str)

        self._system_message = BaseMessage.make_assistant_message(
            role_name="Assistant", content=self.default_system_message
        )

        self.code_executor = CodeExecutionEnvironment(
            agent=self,
            sandbox=sandbox,
            verbose=verbose,
            unsafe_mode=unsafe_mode,
            import_white_list=import_white_list,
            require_confirm=require_confirm,
        )
        self.update_memory(self._system_message, OpenAIBackendRole.SYSTEM)
        self.max_iterations = max_iterations

    def step(
        self,
        input_message: Union[BaseMessage, str],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> ChatAgentResponse:
        r"""Execute a step with code parsing and execution.

        Args:
            input_message: The input message to process
            response_format: The response format to use
        Returns:
            ChatAgentResponse: The response from the code execution
        """

        if isinstance(input_message, str):
            input_message = BaseMessage.make_user_message(
                role_name="User", content=input_message
            )

        # Add user input to memory
        self.update_memory(input_message, OpenAIBackendRole.USER)

        is_final_answer = False
        final_output = None

        # Continue executing code until a final answer is reached
        for _ in range(self.max_iterations):
            try:
                openai_messages, num_tokens = self.memory.get_context()
            except RuntimeError as e:
                return self._step_terminate(
                    e.args[1], [], "max_tokens_exceeded"
                )

            # Get response from model backend
            response = self._get_model_response(
                openai_messages,
                num_tokens,
                response_format,
            )

            try:
                # Get the text content from the response
                content = (
                    response.output_messages[0].content
                    if response.output_messages[0].content
                    else ""
                )
                # Parse code blocks
                code = _parse_code_blobs(content)
                code_action = _fix_final_answer_code(code)
            except Exception as e:
                error_msg = (
                    f"Error in code parsing:\n{e}\n"
                    "Make sure to provide correct code blobs."
                )
                raise ValueError(error_msg)

            logger.info(f"Executing parsed code: {code_action}")

            try:
                output, execution_logs, is_final_answer = (
                    self.code_executor.execute(code_action)
                )
                logger.info(
                    f"output: {output}, \n"
                    f"execution_logs: {execution_logs}, \n"
                    f"is_final_answer: {is_final_answer}"
                )

                execution_outputs_console = []
                if len(execution_logs) > 0:
                    execution_outputs_console += [
                        Text("Execution logs:", style="bold"),
                        Text(execution_logs),
                    ]

                observation = (
                    "This is Observation information:\n"
                    "Execution code:\n" + code_action
                )
                observation += "\nExecution logs:\n" + execution_logs
                observation += "\nLast output from code snippet:\n" + str(
                    output
                )

                execution_outputs_console += [
                    Text(
                        f"{('Out - Final answer' if is_final_answer else 'Out')}: {output}",  # noqa: E501
                        style=("bold #d4b702" if is_final_answer else ""),
                    ),
                ]
                logger.info(Group(*execution_outputs_console))

                # Update agent memory with the execution results
                self.update_memory(
                    BaseMessage.make_assistant_message(
                        role_name="Assistant", content=observation
                    ),
                    OpenAIBackendRole.ASSISTANT,
                )
                if is_final_answer:
                    # Store the final output
                    final_output = BaseMessage.make_assistant_message(
                        content="Here is the final answer: " + str(output),
                        role_name="Assistant",
                    )

                    # Break the loop since we have a final answer
                    break

            except Exception as e:
                if (
                    hasattr(self.code_executor, "state")
                    and "_print_outputs" in self.code_executor.state
                ):
                    execution_logs = str(
                        self.code_executor.state["_print_outputs"]
                    )
                    if len(execution_logs) > 0:
                        execution_outputs_console = [
                            Text("Execution logs:", style="bold"),
                            Text(execution_logs),
                        ]

                        self.update_memory(
                            BaseMessage.make_assistant_message(
                                role_name="Assistant",
                                content=(
                                    "There was an error during execution. "
                                    "Here are the logs:\n"
                                    + execution_logs
                                    + "\n"
                                    + "Error: "
                                    + str(e)
                                ),
                            ),
                            OpenAIBackendRole.ASSISTANT,
                        )
                        logger.info(Group(*execution_outputs_console))

                error_msg = str(e)
                if (
                    "Import of " in error_msg
                    and " is not allowed" in error_msg
                ):
                    logger.info(
                        "[bold red]Warning to user: Code execution failed "
                        "due to an unauthorized import - Consider passing "
                        "said import under `additional_authorized_imports` "
                        "when initializing your CodeAgent."
                    )
                # Continue the loop after error, giving the agent a chance
                # to fix the issue
                continue

        if final_output is None:
            final_output = BaseMessage.make_assistant_message(
                content="No final answer was produced.",
                role_name="Assistant",
            )

        return ChatAgentResponse(
            msgs=[final_output],
            terminated=True,
            info={},
        )
