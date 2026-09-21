# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

"""
MCP Code Agent

An agent that interacts with MCP servers through code execution instead of
direct tool calls. This approach reduces token consumption and enables better
tool composition and state management.

Based on:
- https://www.anthropic.com/engineering/code-execution-with-mcp
- https://arxiv.org/pdf/2506.01056 (MCP-Zero paper)
"""

import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from camel.agents.chat_agent import ChatAgent
from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models.base_model import BaseModelBackend
from camel.models.model_factory import ModelFactory
from camel.prompts import TextPrompt
from camel.responses import ChatAgentResponse
from camel.types import ModelPlatformType, ModelType, RoleType

if TYPE_CHECKING:
    from camel.interpreters.base import BaseInterpreter
    from camel.toolkits.mcp_toolkit import MCPToolkit
    from camel.utils.mcp_skills import SkillManager

logger = get_logger(__name__)

# System message for code-based MCP interaction
CODE_SYSTEM_MESSAGE = """
You are an AI assistant that interacts with MCP (Model Context Protocol)
servers by writing Python code instead of making direct tool calls.

## Your Capabilities

You have access to MCP tools through generated Python modules in the `servers/`
directory. Instead of calling tools directly, you write code that imports and
uses these modules.

You also have access to a `skills/` directory where you can save and reuse
code snippets for common tasks.

## How to Use MCP Tools

1. Explore available tools by checking the servers directory structure
2. Import the tools you need from the appropriate server module
3. Write Python code to call the tools and process their results
4. Return the final result to the user

## Example

Instead of:
```
TOOL_CALL: read_file(path="/example.txt")
```

Write:
```python
from servers.filesystem import read_file

content = await read_file(path="/example.txt")
print(f"File content: {content['result']}")
```

## Benefits

- You can compose multiple tool calls without passing intermediate results
  through context
- You can use Python's control flow (loops, conditionals) to orchestrate tools
- You can save intermediate results to files for later use
- You can develop and save reusable functions in the skills directory

## Guidelines

1. Always use async/await when calling MCP tools
2. Handle errors gracefully
3. Keep intermediate data in variables instead of passing through context
4. Save useful functions as skills for future use
5. Document your code clearly

Now, help the user with their task by writing appropriate Python code.
"""

TOOL_DISCOVERY_PROMPT = """
Available MCP Tools:

{directory_tree}

{tools_summary}

You can import these tools in your code. For example:
```python
from servers.google_drive import get_document
from servers.salesforce import update_record
```
"""

SKILLS_PROMPT = """
Available Skills:

{skills_summary}

You can import these skills in your code. For example:
```python
from skills.my_skill import useful_function
```
"""


class MCPCodeAgent(ChatAgent):
    r"""An agent that uses code execution to interact with MCP servers.

    This agent generates Python code to call MCP tools instead of making
    direct tool calls. This approach:
    - Reduces token consumption (only loads needed tools)
    - Enables better tool composition
    - Supports state persistence
    - Allows skill development

    Args:
        mcp_toolkit (MCPToolkit): The MCP toolkit managing server connections.
        workspace_dir (str): Directory for code execution and skills.
        interpreter (Optional[BaseInterpreter]): Code interpreter to use.
            If None, creates an InternalPythonInterpreter.
            (default: :obj:`None`)
        system_message (Optional[Union[str, BaseMessage]]): Custom system
            message. If None, uses CODE_SYSTEM_MESSAGE.
            (default: :obj:`None`)
        model (Optional[BaseModelBackend]): Model to use for generating
            responses. (default: :obj:`None`)
        enable_skills (bool): Whether to enable skills management.
            (default: :obj:`True`)
        auto_generate_apis (bool): Whether to automatically generate MCP
            APIs on initialization. (default: :obj:`True`)
        **kwargs: Additional arguments passed to ChatAgent.

    Example:
        >>> from camel.toolkits.mcp_toolkit import MCPToolkit
        >>> toolkit = MCPToolkit(config_path="config.json")
        >>> await toolkit.connect()
        >>>
        >>> agent = MCPCodeAgent(
        ...     mcp_toolkit=toolkit,
        ...     workspace_dir="/path/to/workspace"
        ... )
        >>> response = await agent.astep(
        ...     "Read document abc123 from Google Drive and "
        ...     "update Salesforce record"
        ... )
    """

    def __init__(
        self,
        mcp_toolkit: "MCPToolkit",
        workspace_dir: str,
        interpreter: Optional["BaseInterpreter"] = None,
        system_message: Optional[Union[str, BaseMessage]] = None,
        model: Optional[BaseModelBackend] = None,
        enable_skills: bool = True,
        auto_generate_apis: bool = True,
        **kwargs,
    ):
        # Set up model
        if model is None:
            model = ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.DEFAULT,
            )

        # Set up system message
        if system_message is None:
            system_message = BaseMessage(
                role_name="MCPCodeAgent",
                role_type=RoleType.ASSISTANT,
                meta_dict=None,
                content=CODE_SYSTEM_MESSAGE,
            )

        # Initialize parent
        super().__init__(system_message=system_message, model=model, **kwargs)

        # Set up MCP code executor
        from camel.utils.mcp_code_executor import MCPCodeExecutor

        self.mcp_toolkit = mcp_toolkit
        self.workspace_dir = workspace_dir
        self.executor = MCPCodeExecutor(mcp_toolkit, workspace_dir)

        # Set up interpreter
        if interpreter is None:
            from camel.interpreters import InternalPythonInterpreter

            # Create interpreter with MCP-related imports in whitelist
            self.interpreter: "BaseInterpreter" = InternalPythonInterpreter(
                import_white_list=[
                    "servers",
                    "skills",
                    "asyncio",
                    "json",
                    "os",
                    "pathlib",
                    "typing",
                ],
                unsafe_mode=True,  # Allow flexible code execution
            )
        else:
            self.interpreter = interpreter

        # Set up skills manager
        self.enable_skills = enable_skills
        self.skill_manager: Optional["SkillManager"] = None
        if enable_skills:
            from camel.utils.mcp_skills import SkillManager

            skills_dir = f"{workspace_dir}/skills"
            self.skill_manager = SkillManager(skills_dir)

        # Auto-generate APIs flag
        self.auto_generate_apis = auto_generate_apis
        self._apis_generated = False

        logger.info(
            f"Initialized MCPCodeAgent with workspace: {workspace_dir}"
        )

    async def connect(self) -> None:
        r"""Connect to MCP servers and generate code APIs."""
        # Connect toolkit if not already connected
        if not self.mcp_toolkit.is_connected:
            await self.mcp_toolkit.connect()

        # Generate APIs if auto-generation is enabled
        if self.auto_generate_apis and not self._apis_generated:
            await self.executor.generate_apis()
            self._apis_generated = True

        logger.info("MCPCodeAgent connected and ready")

    async def disconnect(self) -> None:
        r"""Disconnect from MCP servers."""
        if self.mcp_toolkit.is_connected:
            await self.mcp_toolkit.disconnect()

        logger.info("MCPCodeAgent disconnected")

    def _get_context_prompt(self) -> str:
        r"""Generate context prompt with available tools and skills.

        Returns:
            str: Formatted context information.
        """
        context_parts = []

        # Add tool discovery information
        workspace_info = self.executor.get_workspace_info()
        directory_tree = workspace_info["directory_tree"]
        available_tools = workspace_info["available_tools"]

        tools_summary = "## Available Tools by Server:\n\n"
        for server, tools in available_tools.items():
            tools_summary += f"### {server}\n"
            for tool in tools:
                tools_summary += f"- {tool}\n"
            tools_summary += "\n"

        tool_prompt = TextPrompt(TOOL_DISCOVERY_PROMPT)
        context_parts.append(
            tool_prompt.format(
                directory_tree=directory_tree, tools_summary=tools_summary
            )
        )

        # Add skills information if enabled
        if self.enable_skills and self.skill_manager:
            skills_summary = self.skill_manager.get_skills_summary()
            skills_prompt = TextPrompt(SKILLS_PROMPT)
            context_parts.append(
                skills_prompt.format(skills_summary=skills_summary)
            )

        return "\n\n".join(context_parts)

    async def astep(
        self, input_message: Union[BaseMessage, str], *args, **kwargs
    ) -> ChatAgentResponse:
        r"""Asynchronous step function with code execution.

        Args:
            input_message (Union[BaseMessage, str]): User's input message.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            ChatAgentResponse: Agent's response.
        """
        # Ensure connected
        if not self.mcp_toolkit.is_connected:
            await self.connect()

        # Prepare message with context
        context = self._get_context_prompt()
        if isinstance(input_message, str):
            full_message = f"{context}\n\n## User Request:\n{input_message}"
        else:
            full_message = (
                f"{context}\n\n## User Request:\n{input_message.content}"
            )

        # Get code from model
        response = await super().astep(full_message, *args, **kwargs)

        # Extract and execute code if present
        if response.msgs:
            content = response.msgs[0].content
            code_blocks = self._extract_code_blocks(str(content))

            if code_blocks:
                # Execute the code
                for code in code_blocks:
                    try:
                        # Execute with async support
                        result = await self._execute_async_code(code)

                        # Add result to context for final response
                        result_message = (
                            f"Code execution completed.\nResult: {result}"
                        )

                        # Get final response with result
                        final_response = await super().astep(
                            result_message, *args, **kwargs
                        )
                        return final_response

                    except Exception as e:
                        error_message = (
                            f"Error executing code: {e}\n"
                            f"Please try a different approach."
                        )
                        logger.error(error_message)

                        # Get error handling response
                        error_response = await super().astep(
                            error_message, *args, **kwargs
                        )
                        return error_response

        return response

    def _extract_code_blocks(self, text: str) -> List[str]:
        r"""Extract Python code blocks from markdown text.

        Args:
            text (str): Text containing code blocks.

        Returns:
            List[str]: List of code blocks.
        """
        import re

        # Find code blocks with python/py language tag
        pattern = r"```(?:python|py)\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)

        return [match.strip() for match in matches]

    async def _execute_async_code(self, code: str) -> Any:
        r"""Execute code that may contain async calls.

        Args:
            code (str): Python code to execute.

        Returns:
            Any: Result of execution.
        """
        # Create execution context with workspace in path
        context = self.executor.get_execution_context()

        # Add async support
        context["asyncio"] = asyncio

        # Check if code contains await
        if "await " in code:
            # Wrap in async function
            wrapped_code = f"""
async def __async_exec():
    {code.replace(chr(10), chr(10) + '    ')}

__result = asyncio.run(__async_exec())
"""
            exec(wrapped_code, context)
            return context.get("__result")
        else:
            # Execute synchronously
            exec(code, context)
            return context.get("result")

    def save_skill(
        self,
        name: str,
        description: str,
        code: str,
        tags: Optional[List[str]] = None,
        examples: Optional[List[str]] = None,
    ) -> bool:
        r"""Save a code snippet as a reusable skill.

        Args:
            name (str): Name of the skill.
            description (str): What the skill does.
            code (str): The Python code.
            tags (Optional[List[str]]): Tags for categorization.
            examples (Optional[List[str]]): Usage examples.

        Returns:
            bool: True if saved successfully.
        """
        if not self.enable_skills or not self.skill_manager:
            logger.warning("Skills are not enabled")
            return False

        from camel.utils.mcp_skills import Skill

        skill = Skill(
            name=name,
            description=description,
            code=code,
            tags=tags or [],
            examples=examples or [],
        )

        return self.skill_manager.save_skill(skill)

    def list_skills(self) -> List[str]:
        r"""List available skills.

        Returns:
            List[str]: List of skill names.
        """
        if not self.enable_skills or not self.skill_manager:
            return []

        return self.skill_manager.list_skills()

    def get_skill(self, name: str) -> Optional[str]:
        r"""Get the code for a specific skill.

        Args:
            name (str): Name of the skill.

        Returns:
            Optional[str]: The skill code, or None if not found.
        """
        if not self.enable_skills or not self.skill_manager:
            return None

        skill = self.skill_manager.load_skill(name)
        return skill.code if skill else None

    async def __aenter__(self):
        r"""Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        r"""Async context manager exit."""
        await self.disconnect()

    @classmethod
    async def create(
        cls,
        config_path: Optional[str] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        workspace_dir: str = "./mcp_workspace",
        **kwargs,
    ) -> "MCPCodeAgent":
        r"""Factory method to create and connect an MCPCodeAgent.

        Args:
            config_path (Optional[str]): Path to MCP config file.
            config_dict (Optional[Dict[str, Any]]): MCP configuration dict.
            workspace_dir (str): Workspace directory.
            **kwargs: Additional arguments for MCPCodeAgent.

        Returns:
            MCPCodeAgent: Connected agent instance.
        """
        from camel.toolkits.mcp_toolkit import MCPToolkit

        # Create toolkit
        toolkit = MCPToolkit(config_path=config_path, config_dict=config_dict)

        # Create agent
        agent = cls(mcp_toolkit=toolkit, workspace_dir=workspace_dir, **kwargs)

        # Connect
        await agent.connect()

        return agent
