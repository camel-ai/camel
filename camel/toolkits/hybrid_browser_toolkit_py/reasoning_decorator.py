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

"""Decorator for adding reasoning capability to browser toolkit actions.

This module provides a decorator that enables agents to provide reasoning
while executing browser actions. The reasoning is stored in the agent's
context, helping to improve decision-making especially for actions that
require waiting for page updates.

Key Features:
    1. Required reasoning parameter for browser actions
    2. Reasoning is injected into agent's memory for chain-of-thought
    3. Wait suggestions when actions may trigger page updates
    4. Internal method calls bypass the requirement automatically

Example:
    >>> from camel.toolkits.hybrid_browser_toolkit_py import (
    ...     HybridBrowserToolkit
    ... )
    >>> from camel.toolkits.hybrid_browser_toolkit_py import (
    ...     enable_reasoning_for_toolkit
    ... )
    >>>
    >>> toolkit = HybridBrowserToolkit()
    >>> toolkit = enable_reasoning_for_toolkit(toolkit)
    >>>
    >>> # Now browser tools require a 'reasoning' parameter
    >>> # The reasoning is stored in context for chain-of-thought
"""

import inspect
import time
from contextvars import ContextVar
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, List, Optional

from camel.logger import get_logger

if TYPE_CHECKING:
    from camel.agents import ChatAgent

logger = get_logger(__name__)

# Context variable to track when we're inside a reasoning-enabled action
# This allows internal method calls to bypass reasoning requirement
_in_reasoning_action: ContextVar[bool] = ContextVar(
    '_in_reasoning_action', default=False
)

# Keywords that suggest waiting may be needed after an action
_WAIT_TRIGGER_KEYWORDS = [
    # Form submission
    'submit',
    'submitting',
    'send',
    'sending',
    'post',
    'posting',
    # Authentication
    'login',
    'logging in',
    'sign in',
    'signing in',
    'authenticate',
    'logout',
    'sign out',
    # Navigation expectations
    'navigate',
    'navigation',
    'redirect',
    'redirecting',
    'page will change',
    'page will update',
    'page will load',
    'new page',
    'next page',
    'another page',
    # Loading expectations
    'load',
    'loading',
    'reload',
    'reloading',
    'refresh',
    'wait for',
    'waiting for',
    'expect',
    'expecting',
    # Form actions
    'confirm',
    'confirming',
    'save',
    'saving',
    'update',
    'updating',
    'delete',
    'deleting',
    'remove',
    'removing',
    # Payment/checkout
    'checkout',
    'payment',
    'pay',
    'purchase',
    'order',
    # Search
    'search',
    'searching',
    'query',
    'filter',
    'filtering',
]

# Actions that commonly require waiting
_WAIT_TRIGGER_ACTIONS = [
    'browser_click',
    'browser_enter',
    'browser_type',  # when followed by enter
    'browser_select',
]


def _should_suggest_wait(action_name: str, reasoning: str) -> bool:
    r"""Determine if a wait suggestion should be added based on the action
    and reasoning.

    Args:
        action_name: Name of the browser action being performed.
        reasoning: The reasoning provided by the agent.

    Returns:
        True if waiting is likely needed after this action.
    """
    # Only suggest waiting for certain actions
    if action_name not in _WAIT_TRIGGER_ACTIONS:
        return False

    # Check if reasoning contains keywords suggesting page changes
    reasoning_lower = reasoning.lower()
    for keyword in _WAIT_TRIGGER_KEYWORDS:
        if keyword in reasoning_lower:
            return True

    return False


def _create_wait_suggestion(action_name: str, reasoning: str) -> str:
    r"""Create a wait suggestion message based on the action and reasoning.

    Args:
        action_name: Name of the browser action performed.
        reasoning: The reasoning provided by the agent.

    Returns:
        A suggestion message for the agent.
    """
    # Identify what kind of wait might be needed
    reasoning_lower = reasoning.lower()

    if any(
        kw in reasoning_lower
        for kw in ['submit', 'login', 'sign in', 'checkout', 'payment']
    ):
        return (
            "WAIT SUGGESTION: This action may trigger a form submission or "
            "authentication. The page will likely update. Consider using "
            "browser_wait_user(timeout_sec=3) to wait for the page to load, "
            "then get a fresh snapshot to see the result."
        )
    elif any(kw in reasoning_lower for kw in ['search', 'filter', 'query']):
        return (
            "WAIT SUGGESTION: This action may trigger a search or filter "
            "operation. Results may take time to load. Consider using "
            "browser_wait_user(timeout_sec=2) before checking the results."
        )
    elif any(
        kw in reasoning_lower
        for kw in ['navigate', 'redirect', 'new page', 'next page']
    ):
        return (
            "WAIT SUGGESTION: This action may cause navigation to a new page. "
            "Use browser_wait_user(timeout_sec=3) to wait for the new page "
            "to load before taking further actions."
        )
    else:
        return (
            "WAIT SUGGESTION: Based on your reasoning, this action may cause "
            "page updates. Consider using browser_wait_user(timeout_sec=2) "
            "if the page doesn't update immediately, then get a fresh "
            "snapshot."
        )


def with_reasoning(func: Callable) -> Callable:
    r"""Decorator that adds a 'reasoning' parameter to browser action methods.

    When the decorated function is called with a 'reasoning' argument,
    the reasoning is logged and optionally stored in the agent's context
    (if an agent is registered with the toolkit).

    This decorator is designed to work with async methods of browser toolkits
    that inherit from RegisteredAgentToolkit.

    Args:
        func: The async method to decorate.

    Returns:
        The wrapped function with 'reasoning' parameter support.

    Example:
        >>> class MyToolkit(BaseToolkit, RegisteredAgentToolkit):
        ...     @with_reasoning
        ...     async def browser_click(self, *, ref: str) -> Dict[str, Any]:
        ...         # Implementation
        ...         pass
        ...
        >>> # Now browser_click accepts an optional 'reasoning' parameter
    """
    # Get the original signature
    original_sig = inspect.signature(func)

    # Check if the function is async
    if not inspect.iscoroutinefunction(func):
        raise TypeError(
            f"with_reasoning decorator can only be applied to async "
            f"functions. '{func.__name__}' is not async."
        )

    # Create new parameters list with 'reasoning' added
    new_params = list(original_sig.parameters.values())

    # Check if 'reasoning' already exists
    if 'reasoning' not in original_sig.parameters:
        # Add 'reasoning' as a required keyword-only parameter (no default)
        reasoning_param = inspect.Parameter(
            'reasoning',
            inspect.Parameter.KEYWORD_ONLY,
            annotation=str,  # Required string, not Optional
        )

        # Insert before **kwargs if it exists, otherwise at the end
        insert_index = len(new_params)
        for i, param in enumerate(new_params):
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                insert_index = i
                break

        new_params.insert(insert_index, reasoning_param)

    # Create new signature
    new_sig = original_sig.replace(parameters=new_params)

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        # Check if inside another reasoning-enabled action (internal call)
        # If so, reasoning is optional to allow internal method calls
        is_internal_call = _in_reasoning_action.get()

        # Extract reasoning from kwargs
        reasoning = kwargs.pop('reasoning', None)

        if reasoning is None:
            if not is_internal_call:
                # External call without reasoning - raise error
                raise TypeError(
                    f"{func.__name__}() missing required keyword "
                    f"argument: 'reasoning'. When reasoning is enabled, "
                    f"you must provide a reasoning string explaining "
                    f"why you are performing this action."
                )
            # Internal call without reasoning - allowed, skip processing
        elif not isinstance(reasoning, str) or not reasoning.strip():
            raise ValueError(
                f"{func.__name__}() requires a non-empty reasoning string. "
                f"Please provide a clear explanation for this action."
            )
        else:
            # Process the reasoning
            action_name = func.__name__
            _process_reasoning(self, action_name, reasoning)

        # Set context to indicate we're in a reasoning action
        # This allows internal calls to bypass reasoning requirement
        token = _in_reasoning_action.set(True)
        try:
            # Execute the original function
            result = await func(self, *args, **kwargs)
        finally:
            # Reset context
            _in_reasoning_action.reset(token)

        # Add wait suggestion if appropriate (only for external calls with
        # reasoning)
        if reasoning and _should_suggest_wait(func.__name__, reasoning):
            wait_suggestion = _create_wait_suggestion(func.__name__, reasoning)
            logger.info(f"[WAIT SUGGESTION] {wait_suggestion}")

            # Add to result if it's a dict
            if isinstance(result, dict):
                result['wait_suggestion'] = wait_suggestion

            # Also inject the suggestion into agent context
            agent: Optional["ChatAgent"] = getattr(self, '_agent', None)
            if agent is None and hasattr(self, 'agent'):
                agent = getattr(self, 'agent', None)

            if agent is not None:
                try:
                    _inject_wait_suggestion_to_context(
                        agent, func.__name__, wait_suggestion
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to inject wait suggestion into context: {e}"
                    )

        return result

    # Apply the new signature
    wrapper.__signature__ = new_sig  # type: ignore[attr-defined]

    # Mark as enhanced
    wrapper.__reasoning_enhanced__ = True  # type: ignore[attr-defined]

    # Enhance docstring
    if func.__doc__:
        enhanced_doc = func.__doc__.rstrip()
        # Add reasoning parameter documentation
        reasoning_doc = (
            "\n        reasoning (str): **Required.** Agent's reasoning "
            "for this action.\n            The reasoning is stored in the "
            "agent's context, helping to\n            maintain a chain of "
            "thought during browser automation."
        )

        # Find Args section and add to it
        if 'Args:' in enhanced_doc:
            # Find position after last existing arg
            lines = enhanced_doc.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith('Returns:'):
                    # Insert before Returns
                    lines.insert(i, reasoning_doc)
                    break
            else:
                # No Returns section, add at end
                lines.append(reasoning_doc)
            enhanced_doc = '\n'.join(lines)
        else:
            # No Args section exists
            enhanced_doc += f"\n\n    Args:{reasoning_doc}"

        wrapper.__doc__ = enhanced_doc

    return wrapper


def _process_reasoning(
    toolkit_instance: Any,
    action_name: str,
    reasoning: str,
) -> None:
    r"""Process and store reasoning in the agent's context.

    Args:
        toolkit_instance: The toolkit instance (must have 'agent' attr).
        action_name: Name of the action being performed.
        reasoning: The reasoning text provided by the agent.
    """
    # Log the reasoning
    logger.info(f"[REASONING] {action_name}: {reasoning}")

    # Store in agent context if an agent is registered
    agent: Optional["ChatAgent"] = getattr(toolkit_instance, '_agent', None)
    if agent is None:
        # Try the 'agent' property
        if hasattr(toolkit_instance, 'agent'):
            agent = getattr(toolkit_instance, 'agent', None)

    if agent is not None:
        try:
            _inject_reasoning_to_context(agent, action_name, reasoning)
        except Exception as e:
            logger.warning(
                f"Failed to inject reasoning into agent context: {e}"
            )
    else:
        logger.debug(
            "No agent registered with toolkit - reasoning logged only, "
            "not stored in context."
        )


def _inject_reasoning_to_context(
    agent: "ChatAgent",
    action_name: str,
    reasoning: str,
) -> None:
    r"""Inject reasoning into the agent's memory/context.

    This creates an assistant message with the reasoning and writes it
    to the agent's memory, making it part of the conversation history.

    Args:
        agent: The ChatAgent instance.
        action_name: Name of the action being performed.
        reasoning: The reasoning text.
    """
    from camel.memories import MemoryRecord
    from camel.messages import BaseMessage
    from camel.types import OpenAIBackendRole

    # Format the reasoning as a message
    reasoning_content = f"[Action Reasoning - {action_name}]\n{reasoning}"

    # Create an assistant message with the reasoning
    reasoning_message = BaseMessage.make_assistant_message(
        role_name="assistant",
        content=reasoning_content,
    )

    # Create a memory record
    record = MemoryRecord(
        message=reasoning_message,
        role_at_backend=OpenAIBackendRole.ASSISTANT,
        timestamp=time.time_ns() / 1_000_000_000,
        agent_id=getattr(agent, 'agent_id', 'unknown'),
    )

    # Write to memory
    agent.memory.write_record(record)
    logger.debug(f"Reasoning injected into agent context for {action_name}")


def _inject_wait_suggestion_to_context(
    agent: "ChatAgent",
    action_name: str,
    wait_suggestion: str,
) -> None:
    r"""Inject wait suggestion into the agent's memory/context.

    This creates a system-like message with the wait suggestion and writes it
    to the agent's memory, helping the agent decide when to use
    browser_wait_user.

    Args:
        agent: The ChatAgent instance.
        action_name: Name of the action that was performed.
        wait_suggestion: The wait suggestion text.
    """
    from camel.memories import MemoryRecord
    from camel.messages import BaseMessage
    from camel.types import OpenAIBackendRole

    # Format the suggestion as a message
    suggestion_content = (
        f"[System Hint - After {action_name}]\n{wait_suggestion}"
    )

    # Create an assistant message with the suggestion
    # Using assistant role so it appears as part of the agent's thinking
    suggestion_message = BaseMessage.make_assistant_message(
        role_name="assistant",
        content=suggestion_content,
    )

    # Create a memory record
    record = MemoryRecord(
        message=suggestion_message,
        role_at_backend=OpenAIBackendRole.ASSISTANT,
        timestamp=time.time_ns() / 1_000_000_000,
        agent_id=getattr(agent, 'agent_id', 'unknown'),
    )

    # Write to memory
    agent.memory.write_record(record)
    logger.debug(
        f"Wait suggestion injected into agent context after {action_name}"
    )


def enable_reasoning_for_toolkit(
    toolkit,
    tool_names: Optional[List[str]] = None,
) -> Any:
    r"""Enable reasoning for specific browser toolkit methods.

    This function modifies a browser toolkit instance to add reasoning
    support to its methods. When enabled, agents can provide optional
    reasoning when calling browser actions.

    Args:
        toolkit: The browser toolkit instance to enhance.
        tool_names: List of tool names to enhance. If None, enhances
            all browser action tools.

    Returns:
        The same toolkit instance with reasoning support added.

    Example:
        >>> toolkit = HybridBrowserToolkit()
        >>> toolkit = enable_reasoning_for_toolkit(toolkit)
        >>>
        >>> # Now the toolkit's tools support reasoning
        >>> result = await toolkit.browser_click(
        ...     ref="e1",
        ...     reasoning="Clicking submit button to submit the form"
        ... )
    """
    # Default browser action tools to enhance with reasoning
    default_tools = [
        "browser_open",
        "browser_close",
        "browser_click",
        "browser_type",
        "browser_select",
        "browser_scroll",
        "browser_enter",
        "browser_visit_page",
        "browser_back",
        "browser_forward",
        "browser_wait_user",
        "browser_press_key",
        "browser_mouse_control",
        "browser_mouse_drag",
        "browser_console_exec",
    ]

    tools_to_enhance = tool_names if tool_names is not None else default_tools

    import types

    for tool_name in tools_to_enhance:
        if hasattr(toolkit, tool_name):
            method = getattr(toolkit, tool_name)

            # Skip if already enhanced
            if getattr(method, '__reasoning_enhanced__', False):
                continue

            # Check if it's an async method
            if inspect.iscoroutinefunction(method):
                # Get the underlying function from the bound method
                # If it's bound, get __func__, otherwise use it directly
                if hasattr(method, '__func__'):
                    underlying_func = method.__func__
                else:
                    underlying_func = method

                # Apply the with_reasoning decorator
                enhanced_func = with_reasoning(underlying_func)

                # Bind the enhanced function to the toolkit instance
                bound_method = types.MethodType(enhanced_func, toolkit)
                setattr(toolkit, tool_name, bound_method)
                logger.debug(f"Enhanced {tool_name} with reasoning support")
            else:
                logger.debug(f"Skipping {tool_name} - not an async method")

    # Mark toolkit as enhanced
    toolkit._reasoning_enabled = True

    return toolkit


class ReasoningContextManager:
    r"""Context manager for collecting reasoning during a browser session.

    This class provides a way to collect and store all reasoning provided
    during a browser automation session, which can be useful for debugging
    or analysis.

    Example:
        >>> with ReasoningContextManager() as ctx:
        ...     result = await toolkit.browser_click(
        ...         ref="e1",
        ...         reasoning="Clicking login button"
        ...     )
        ...     ctx.add_reasoning("browser_click", "Clicking login button")
        ...
        >>> print(ctx.get_all_reasoning())
    """

    def __init__(self):
        self._reasoning_log: List[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def add_reasoning(self, action_name: str, reasoning: str) -> None:
        r"""Add a reasoning entry to the log.

        Args:
            action_name: Name of the action.
            reasoning: The reasoning text.
        """
        self._reasoning_log.append(
            {
                "action": action_name,
                "reasoning": reasoning,
                "timestamp": time.time(),
            }
        )

    def get_all_reasoning(self) -> List[dict]:
        r"""Get all reasoning entries.

        Returns:
            List of reasoning entries with action names and timestamps.
        """
        return self._reasoning_log.copy()

    def clear(self) -> None:
        r"""Clear all reasoning entries."""
        self._reasoning_log.clear()
