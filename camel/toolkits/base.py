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

import inspect
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    TypeVar,
)

from docstring_parser import parse

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.utils import AgentOpsMeta, Constants, with_timeout

if TYPE_CHECKING:
    from camel.agents import ChatAgent

F = TypeVar('F', bound=Callable)

logger = get_logger(__name__)


def manual_timeout(func: F) -> F:
    r"""Decorator to mark a function as having manual timeout handling.

    Use this decorator on toolkit methods that manage their own timeout logic
    internally but don't have a `timeout` parameter in their signature.
    This prevents the automatic `with_timeout` wrapper from being applied
    by `BaseToolkit`.

    Note:
        Methods with a `timeout` parameter in their signature are
        automatically detected and skipped, so they don't need this
        decorator.

    Args:
        func (F): The function to mark as having manual timeout handling.

    Returns:
        F: The same function with `_manual_timeout` attribute set to True.

    Example:
        >>> class MyToolkit(BaseToolkit):
        ...     @manual_timeout
        ...     def long_running_task(self, max_wait: int = 30):
        ...         # This method manages timeout internally using max_wait
        ...         # but doesn't use 'timeout' as the parameter name
        ...         pass
    """
    func._manual_timeout = True  # type: ignore[attr-defined]
    return func


class BaseToolkit(metaclass=AgentOpsMeta):
    r"""Base class for toolkits.

    Args:
        timeout (Optional[float]): The timeout for the toolkit.
    """

    from mcp.server import FastMCP

    mcp: FastMCP
    timeout: Optional[float] = Constants.TIMEOUT_THRESHOLD

    def __init__(self, timeout: Optional[float] = Constants.TIMEOUT_THRESHOLD):
        # check if timeout is a positive number
        if timeout is not None and timeout <= 0:
            raise ValueError("Timeout must be a positive number.")
        self.timeout = timeout

    # Add timeout to all callable methods in the toolkit
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for attr_name, attr_value in cls.__dict__.items():
            if callable(attr_value) and not attr_name.startswith("__"):
                # Skip methods that have manual timeout management
                if getattr(attr_value, '_manual_timeout', False):
                    continue
                # Auto-detect: skip methods that have 'timeout' in signature
                try:
                    sig = inspect.signature(attr_value)
                    if 'timeout' in sig.parameters:
                        continue
                except (ValueError, TypeError):
                    # Some built-in functions don't have signatures
                    pass
                setattr(cls, attr_name, with_timeout(attr_value))

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def run_mcp_server(
        self, mode: Literal["stdio", "sse", "streamable-http"]
    ) -> None:
        r"""Run the MCP server in the specified mode.

        Args:
            mode (Literal["stdio", "sse", "streamable-http"]): The mode to run
                the MCP server in.
        """
        self.mcp.run(mode)

    def _get_skill_state_path(
        self, session_id: str = "default", state_dir: Optional[str] = None
    ) -> Path:
        r"""Get the state file path for this toolkit."""
        base_dir = (
            Path(state_dir or tempfile.gettempdir()) / "camel_skill_state"
        )
        base_dir.mkdir(parents=True, exist_ok=True)
        safe_name = self.__class__.__name__.replace(" ", "_")
        return base_dir / f"{safe_name}_{session_id}.json"

    def save_state(
        self,
        state: Dict[str, Any],
        session_id: str = "default",
        state_dir: Optional[str] = None,
    ) -> Path:
        r"""Save state to a JSON file.

        Args:
            state: Dictionary of state to save.
            session_id: Session identifier.
            state_dir: Optional custom directory for state files.

        Returns:
            Path to the saved state file.
        """
        state_file = self._get_skill_state_path(session_id, state_dir)
        data = {
            "toolkit": self.__class__.__name__,
            "session_id": session_id,
            "updated_at": datetime.now().isoformat(),
            "state": state,
        }
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return state_file

    def load_state(
        self,
        session_id: str = "default",
        state_dir: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        r"""Load state from a JSON file.

        Args:
            session_id: Session identifier.
            state_dir: Optional custom directory for state files.

        Returns:
            The state dictionary if found, None otherwise.
        """
        state_file = self._get_skill_state_path(session_id, state_dir)
        if not state_file.exists():
            return None
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("state")
        except (json.JSONDecodeError, KeyError):
            return None

    def to_skill(
        self,
        output_dir: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        content: Optional[str] = None,
    ) -> Path:
        r"""Convert this toolkit to a skill file.

        Generates a markdown file documenting the toolkit's tools, which can
        be used as a skill/plugin for AI coding assistants.

        Args:
            output_dir: Directory to write the skill file. Defaults to
                `./skills/` in the current directory.
            name: Custom skill name. Defaults to toolkit class name in
                kebab-case.
            description: Custom description. Defaults to class docstring.
            content: Custom skill content. If None, auto-generates from
                tool docstrings.

        Returns:
            Path to the generated skill file.

        Example:
            >>> from camel.toolkits import MathToolkit
            >>> toolkit = MathToolkit()
            >>> skill_path = toolkit.to_skill(name="math")
        """
        # Generate skill name
        if not name:
            class_name = self.__class__.__name__
            if class_name.endswith('Toolkit'):
                class_name = class_name[:-7]
            name = ''.join(
                f'-{c.lower()}' if c.isupper() else c for c in class_name
            ).lstrip('-')

        # Generate description from class docstring
        if not description:
            class_doc = self.__class__.__doc__ or ""
            parsed_doc = parse(class_doc)
            description = parsed_doc.short_description or f"{name} toolkit"

        # Generate content from tool docstrings if not provided
        if not content:
            content = self._generate_skill_content(name, description)

        # Write skill file
        skills_dir = Path(output_dir) if output_dir else Path.cwd() / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skills_dir / f"{name}.md"

        with open(skill_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Skill written to {skill_file}")
        return skill_file

    def _generate_skill_content(self, name: str, description: str) -> str:
        r"""Generate skill content from tool docstrings."""
        lines = [f"# {name}", "", description, "", "## Available Tools", ""]

        for tool in self.get_tools():
            method = tool.func
            method_name = method.__name__
            docstring = method.__doc__ or ""
            parsed = parse(docstring)

            # Signature
            try:
                sig = inspect.signature(method)
                params = [p for n, p in sig.parameters.items() if n != 'self']
                sig_str = ", ".join(str(p) for p in params)
            except (ValueError, TypeError):
                sig_str = "..."

            lines.append(f"### {method_name}")
            lines.append(f"`{method_name}({sig_str})`")
            lines.append("")

            if parsed.short_description:
                lines.append(parsed.short_description)
                lines.append("")

            if parsed.params:
                lines.append("**Parameters:**")
                for p in parsed.params:
                    ptype = p.type_name or "Any"
                    pdesc = p.description or ""
                    lines.append(f"- `{p.arg_name}` ({ptype}): {pdesc}")
                lines.append("")

            if parsed.returns:
                rtype = parsed.returns.type_name or "Any"
                rdesc = parsed.returns.description or ""
                lines.append(f"**Returns:** ({rtype}) {rdesc}")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)


class RegisteredAgentToolkit:
    r"""Mixin class for toolkits that need to register a ChatAgent.

    This mixin provides a standard interface for toolkits that require
    a reference to a ChatAgent instance. The ChatAgent will check if a
    toolkit has this mixin and automatically register itself.
    """

    def __init__(self):
        self._agent: Optional["ChatAgent"] = None

    @property
    def agent(self) -> Optional["ChatAgent"]:
        r"""Get the registered ChatAgent instance.

        Returns:
            Optional[ChatAgent]: The registered agent, or None if not
                registered.

        Note:
            If None is returned, it means the toolkit has not been registered
            with a ChatAgent yet. Make sure to pass this toolkit to a ChatAgent
            via the toolkits parameter during initialization.
        """
        if self._agent is None:
            logger.warning(
                f"{self.__class__.__name__} does not have a "
                f"registered ChatAgent. "
                f"Please ensure this toolkit is passed to a ChatAgent via the "
                f"'toolkits_to_register_agent' parameter during ChatAgent "
                f"initialization if you want to use the tools that require a "
                f"registered agent."
            )
        return self._agent

    def register_agent(self, agent: "ChatAgent") -> None:
        r"""Register a ChatAgent with this toolkit.

        This method allows registering an agent after initialization. The
        ChatAgent will automatically call this method if the toolkit to
        register inherits from RegisteredAgentToolkit.

        Args:
            agent (ChatAgent): The ChatAgent instance to register.
        """
        self._agent = agent
        logger.info(f"Agent registered with {self.__class__.__name__}")
