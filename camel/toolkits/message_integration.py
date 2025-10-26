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
import inspect
from functools import wraps
from typing import Callable, List, Optional, Union

from camel.logger import get_logger
from camel.toolkits import BaseToolkit, FunctionTool

logger = get_logger(__name__)


class ToolkitMessageIntegration:
    r"""Integrates user messaging capabilities into CAMEL toolkits and
    functions.

    This class allows agents to send status updates to users while executing
    toolkit functions in a single step, improving communication and reducing
    the number of tool calls needed.

    Supports both built-in and custom message handlers with flexible parameter
    names. Can update both toolkit methods and standalone functions.

    Example:
        >>> # Using default message handler with toolkit
        >>> message_integration = ToolkitMessageIntegration()
        >>> search_with_messaging = message_integration.
        register_toolkits(
        ...     SearchToolkit()
        ... )

        >>> # Using with standalone functions
        >>> def search_web(query: str) -> list:
        ...     return ["result1", "result2"]
        ...
        >>> enhanced_tools = message_integration.register_functions
        ([search_web])

        >>> # Using custom message handler with different parameters
        >>> def notify_user(severity: str, action: str, details: str = "") ->
        str:
        ...     '''Send notification to user.
        ...
        ...     Args:
        ...         severity: Notification level (info/warning/error)
        ...         action: What action is being performed
        ...         details: Additional details
        ...     '''
        ...     print(f"[{severity}] {action}: {details}")
        ...     return "Notified"
        ...
        >>> message_integration = ToolkitMessageIntegration(
        ...     message_handler=notify_user,
        ...     extract_params_callback=lambda kwargs: (
        ...         kwargs.pop('severity', 'info'),
        ...         kwargs.pop('action', 'executing'),
        ...         kwargs.pop('details', '')
        ...     )
        ... )
    """

    def __init__(
        self,
        message_handler: Optional[Callable] = None,
        extract_params_callback: Optional[Callable[[dict], tuple]] = None,
    ):
        r"""Initialize the toolkit message integration.

        Args:
            message_handler (Optional[Callable]): Custom message handler
                function. If not provided, uses the built-in
                send_message_to_user. (default: :obj:`None`)
            extract_params_callback (Optional[Callable]): Function to extract
                parameters from kwargs for the custom message handler. Should
                return a tuple of arguments to pass to the message handler. If
                not provided, uses default extraction for built-in handler.
                (default: :obj:`None`)
        """
        self.message_handler = message_handler or self.send_message_to_user
        self.extract_params_callback = (
            extract_params_callback or self._default_extract_params
        )

        # If custom handler is provided, we'll use its signature and docstring
        self.use_custom_handler = message_handler is not None

    def _default_extract_params(self, kwargs: dict) -> tuple:
        r"""Default parameter extraction for built-in message handler."""
        return (
            kwargs.pop('message_title', ''),
            kwargs.pop('message_description', ''),
            kwargs.pop('message_attachment', ''),
        )

    def send_message_to_user(
        self,
        message_title: str,
        message_description: str,
        message_attachment: str = "",
    ) -> str:
        r"""Built-in message handler that sends tidy messages to the user.

        This one-way tool keeps the user informed about agent progress,
        decisions, or actions. It does not require a response.

        Args:
            message_title (str): The title of the message.
            message_description (str): The short description message.
            message_attachment (str): The additional attachment of the message,
                which can be a file path or a URL.

        Returns:
            str: Confirmation that the message was successfully sent.
        """
        print(f"\nAgent Message:\n{message_title}\n{message_description}\n")
        if message_attachment:
            print(message_attachment)

        logger.info(
            f"\nAgent Message:\n{message_title} "
            f"{message_description} {message_attachment}"
        )

        return (
            f"Message successfully sent to user: '{message_title} "
            f"{message_description} {message_attachment}'"
        )

    def get_message_tool(self) -> FunctionTool:
        r"""Get the send_message_to_user as a standalone FunctionTool.

        This can be used when you want to provide the messaging capability
        as a separate tool rather than integrating it into other tools.

        Returns:
            FunctionTool: The message sending tool.
        """
        return FunctionTool(self.send_message_to_user)

    def register_toolkits(self, toolkit: BaseToolkit) -> BaseToolkit:
        r"""Add messaging capabilities to all toolkit methods.

        This method modifies a toolkit so that all its tools can send
        status messages to users while executing their primary function.
        The tools will accept optional messaging parameters:
        - message_title: Title of the status message
        - message_description: Description of what the tool is doing
        - message_attachment: Optional file path or URL

        Args:
            toolkit: The toolkit to add messaging capabilities to

        Returns:
            The same toolkit instance with messaging capabilities added to
                all methods.
        """
        original_tools = toolkit.get_tools()
        enhanced_methods = {}
        for tool in original_tools:
            method_name = tool.func.__name__
            enhanced_func = self._add_messaging_to_tool(tool.func)
            enhanced_methods[method_name] = enhanced_func
            setattr(toolkit, method_name, enhanced_func)
        original_get_tools_method = toolkit.get_tools

        def enhanced_get_tools() -> List[FunctionTool]:
            tools = []
            for _, enhanced_method in enhanced_methods.items():
                tools.append(FunctionTool(enhanced_method))
            original_tools_list = original_get_tools_method()
            for tool in original_tools_list:
                if tool.func.__name__ not in enhanced_methods:
                    tools.append(tool)

            return tools

        toolkit.get_tools = enhanced_get_tools  # type: ignore[method-assign]

        # Also handle clone_for_new_session
        # if it exists to ensure cloned toolkits
        # also have message integration
        if hasattr(toolkit, 'clone_for_new_session'):
            original_clone_method = toolkit.clone_for_new_session
            message_integration_instance = self

            def enhanced_clone_for_new_session(new_session_id=None):
                cloned_toolkit = original_clone_method(new_session_id)
                return message_integration_instance.register_toolkits(
                    cloned_toolkit
                )

            toolkit.clone_for_new_session = enhanced_clone_for_new_session

        return toolkit

    def _create_bound_method_wrapper(
        self, enhanced_func: Callable, toolkit_instance
    ) -> Callable:
        r"""Create a wrapper that mimics a bound method for _clone_tools.

        This wrapper preserves the toolkit instance reference while maintaining
        the enhanced messaging functionality.
        """

        # Create a wrapper that appears as a bound method to _clone_tools
        @wraps(enhanced_func)
        def bound_method_wrapper(*args, **kwargs):
            return enhanced_func(*args, **kwargs)

        # Make it appear as a bound method by setting __self__
        bound_method_wrapper.__self__ = toolkit_instance  # type: ignore[attr-defined]

        # Preserve other important attributes
        if hasattr(enhanced_func, '__signature__'):
            bound_method_wrapper.__signature__ = enhanced_func.__signature__  # type: ignore[attr-defined]
        if hasattr(enhanced_func, '__doc__'):
            bound_method_wrapper.__doc__ = enhanced_func.__doc__

        return bound_method_wrapper

    def register_functions(
        self,
        functions: Union[List[FunctionTool], List[Callable]],
        function_names: Optional[List[str]] = None,
    ) -> List[FunctionTool]:
        r"""Add messaging capabilities to a list of functions or FunctionTools.

        This method enhances functions so they can send status messages to
        users while executing. The enhanced functions will accept optional
        messaging parameters that trigger status updates.

        Args:
            functions (Union[List[FunctionTool], List[Callable]]): List of
                FunctionTool objects or callable functions to enhance.
            function_names (Optional[List[str]]): List of specific function
                names to modify. If None, messaging is added to all functions.

        Returns:
            List[FunctionTool]: List of enhanced FunctionTool objects

        Example:
            >>> # With FunctionTools
            >>> tools = [FunctionTool(search_func), FunctionTool(analyze_func)]
            >>> enhanced_tools = message_integration.register_functions
            (tools)

            >>> # With callable functions
            >>> funcs = [search_web, analyze_data, generate_report]
            >>> enhanced_tools = message_integration.register_functions
            (
            ...     funcs,
            ...     function_names=['search_web', 'analyze_data']
            ... )
        """
        enhanced_tools = []

        for item in functions:
            # Extract the function based on input type
            if isinstance(item, FunctionTool):
                func = item.func
            elif callable(item):
                func = item
            else:
                raise ValueError(
                    f"Invalid item type: {type(item)}. Expected "
                    f"FunctionTool or callable."
                )

            # Check if this function should be enhanced
            if function_names is None or func.__name__ in function_names:
                enhanced_func = self._add_messaging_to_tool(func)
                enhanced_tools.append(FunctionTool(enhanced_func))
            else:
                # Return as FunctionTool regardless of input type
                if isinstance(item, FunctionTool):
                    enhanced_tools.append(item)
                else:
                    enhanced_tools.append(FunctionTool(func))

        return enhanced_tools

    def _add_messaging_to_tool(self, func: Callable) -> Callable:
        r"""Add messaging parameters to a tool function.

        This internal method modifies the function signature and docstring
        to include optional messaging parameters that trigger status updates.
        """
        if getattr(func, "__message_integration_enhanced__", False):
            logger.debug(
                f"Function {func.__name__} already enhanced, skipping"
            )
            return func

        # Get the original signature
        original_sig = inspect.signature(func)

        # Check if the function is async
        is_async = inspect.iscoroutinefunction(func)

        # Create new parameters for the enhanced function
        new_params = list(original_sig.parameters.values())

        # Determine which parameters to add based on handler type
        if self.use_custom_handler:
            # Use the custom handler's signature
            handler_sig = inspect.signature(self.message_handler)
            message_params = []

            # Add parameters from the custom handler (excluding self if it's a
            # method)
            for param_name, param in handler_sig.parameters.items():
                if param_name != 'self':
                    # Create a keyword-only parameter with the same annotation
                    # and default
                    new_param = inspect.Parameter(
                        param_name,
                        inspect.Parameter.KEYWORD_ONLY,
                        default=param.default
                        if param.default != inspect.Parameter.empty
                        else None,
                        annotation=param.annotation
                        if param.annotation != inspect.Parameter.empty
                        else inspect.Parameter.empty,
                    )
                    message_params.append(new_param)
        else:
            # Use default parameters for built-in handler
            message_params = [
                inspect.Parameter(
                    'message_title',
                    inspect.Parameter.KEYWORD_ONLY,
                    default="",
                    annotation=str,
                ),
                inspect.Parameter(
                    'message_description',
                    inspect.Parameter.KEYWORD_ONLY,
                    default="",
                    annotation=str,
                ),
                inspect.Parameter(
                    'message_attachment',
                    inspect.Parameter.KEYWORD_ONLY,
                    default="",
                    annotation=str,
                ),
            ]

        # Find where to insert the new parameters (before **kwargs if it
        # exists)
        insert_index = len(new_params)
        for i, param in enumerate(new_params):
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                insert_index = i
                break

        # Insert the message parameters
        for param in reversed(message_params):
            new_params.insert(insert_index, param)

        # Create the new signature
        new_sig = original_sig.replace(parameters=new_params)

        if is_async:

            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    params = self.extract_params_callback(kwargs)
                except KeyError:
                    return await func(*args, **kwargs)

                # Check if we should send a message
                should_send = False
                if self.use_custom_handler:
                    should_send = any(
                        p is not None and p != '' for p in params
                    )
                else:
                    # For default handler, params
                    # (title, description, attachment)
                    should_send = bool(params[0]) or bool(params[1])

                # Send message if needed (handle async properly)
                if should_send:
                    try:
                        if self.use_custom_handler:
                            # Check if message handler is async
                            if inspect.iscoroutinefunction(
                                self.message_handler
                            ):
                                await self.message_handler(*params)
                            else:
                                self.message_handler(*params)
                        else:
                            # For built-in handler, provide defaults
                            title, desc, attach = params
                            self.message_handler(
                                title or "Executing Tool",
                                desc or f"Running {func.__name__}",
                                attach or '',
                            )
                    except Exception as msg_error:
                        # Don't let message handler
                        # errors break the main function
                        logger.warning(f"Message handler error: {msg_error}")

                # Execute the original function
                # (kwargs have been modified to remove message params)
                result = await func(*args, **kwargs)

                return result
        else:

            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract parameters using the callback
                # (this will modify kwargs by removing message params)
                try:
                    params = self.extract_params_callback(kwargs)
                except KeyError:
                    # If parameters are missing,
                    # just execute the original function
                    return func(*args, **kwargs)

                # Check if we should send a message
                should_send = False
                if self.use_custom_handler:
                    should_send = any(
                        p is not None and p != '' for p in params
                    )
                else:
                    should_send = bool(params[0]) or bool(params[1])

                # Send message if needed
                if should_send:
                    try:
                        if self.use_custom_handler:
                            self.message_handler(*params)
                        else:
                            # For built-in handler, provide defaults
                            title, desc, attach = params
                            self.message_handler(
                                title or "Executing Tool",
                                desc or f"Running {func.__name__}",
                                attach or '',
                            )
                    except Exception as msg_error:
                        logger.warning(f"Message handler error: {msg_error}")

                result = func(*args, **kwargs)

                return result

        # Apply the new signature to the wrapper
        wrapper.__signature__ = new_sig  # type: ignore[attr-defined]

        # Mark this function as enhanced by message integration
        wrapper.__message_integration_enhanced__ = True  # type: ignore[attr-defined]

        # Create a hybrid approach:
        # store toolkit instance info but preserve calling behavior
        # We'll use a property-like
        # approach to make __self__ available when needed
        if hasattr(func, '__self__'):
            toolkit_instance = func.__self__

            # Store the toolkit instance as an attribute
            # Use setattr to avoid MyPy type checking issues
            wrapper.__toolkit_instance__ = toolkit_instance  # type: ignore[attr-defined]

            # Create a dynamic __self__ property
            # that only appears during introspection
            # but doesn't interfere with normal function calls
            def get_self():
                return toolkit_instance

            # Only set __self__
            # if we're being called in an introspection context
            # (like from _clone_tools)
            # Use setattr to avoid MyPy type checking issues
            wrapper.__self__ = toolkit_instance  # type: ignore[attr-defined]

        # Enhance the docstring
        if func.__doc__:
            enhanced_doc = func.__doc__.rstrip()
            lines = enhanced_doc.split('\n')

            # Find where to insert parameters
            insert_idx = self._find_docstring_insert_point(lines)

            # Check if we need to create an Args section
            has_args_section = any(
                'Args:' in line
                or 'Arguments:' in line
                or 'Parameters:' in line
                for line in lines
            )

            if not has_args_section and insert_idx is not None:
                # Need to create Args section
                base_indent = self._get_base_indent(lines)

                # Add blank line before Args section if needed
                if insert_idx > 0 and lines[insert_idx - 1].strip():
                    lines.insert(insert_idx, "")
                    insert_idx += 1

                # Add Args section header
                lines.insert(insert_idx, f"{base_indent}Args:")
                insert_idx += 1

            # Get parameter documentation
            if self.use_custom_handler and self.message_handler.__doc__:
                # Extract parameter docs from custom handler's docstring
                param_docs = self._extract_param_docs_from_handler()
            else:
                # Use default parameter docs
                param_docs = [
                    "message_title (str, optional): Title for status "
                    "message to user.",
                    "message_description (str, optional): Description for "
                    "status message.",
                    "message_attachment (str, optional): File path or URL to "
                    "attach to message.",
                ]

            # Insert the parameter documentation
            if insert_idx is not None and param_docs:
                # Get proper indentation for parameters
                indent = self._get_docstring_indent(lines, insert_idx)

                # Insert each parameter doc with proper indentation
                for doc in param_docs:
                    lines.insert(insert_idx, f"{indent}{doc}")
                    insert_idx += 1

            wrapper.__doc__ = '\n'.join(lines)

        return wrapper

    def _find_docstring_insert_point(self, lines: List[str]) -> Optional[int]:
        r"""Find where to insert parameters in a docstring."""
        current_indent = ""

        # First, look for existing Args section
        for i, line in enumerate(lines):
            if (
                'Args:' in line
                or 'Arguments:' in line
                or 'Parameters:' in line
            ):
                current_indent = line[: len(line) - len(line.lstrip())]
                # Find where Args section ends by looking for the last
                # parameter
                last_param_idx = None
                for j in range(i + 1, len(lines)):
                    stripped = lines[j].strip()
                    # If it's an empty line, skip it
                    if not stripped:
                        continue
                    # If it's a parameter line (has proper indentation and
                    # content)
                    if lines[j].startswith(current_indent + ' '):
                        last_param_idx = j
                    else:
                        # Hit a line with different indentation or a new
                        # section
                        if last_param_idx is not None:
                            return last_param_idx + 1
                        else:
                            # No parameters found, insert right after Args:
                            return i + 1
                # Args is the last section, return after last parameter
                if last_param_idx is not None:
                    return last_param_idx + 1
                else:
                    # No parameters found, insert right after Args:
                    return i + 1

        # No Args section, need to create one
        # Try to insert before Returns/Yields/Raises/Examples sections
        for i, line in enumerate(lines):
            stripped = line.strip()
            if any(
                section in line
                for section in [
                    'Returns:',
                    'Return:',
                    'Yields:',
                    'Raises:',
                    'Examples:',
                    'Example:',
                    'Note:',
                    'Notes:',
                ]
            ):
                return i

        # No special sections, add at the end
        return len(lines)

    def _get_docstring_indent(self, lines: List[str], insert_idx: int) -> str:
        r"""Get the proper indentation for docstring parameters."""
        # Look for Args: or similar section to match indentation
        for i, line in enumerate(lines):
            if (
                'Args:' in line
                or 'Arguments:' in line
                or 'Parameters:' in line
            ):
                base_indent = line[: len(line) - len(line.lstrip())]
                # Look at the next line to see parameter indentation
                if i + 1 < len(lines):
                    if lines[i + 1].strip():
                        next_indent = lines[i + 1][
                            : len(lines[i + 1]) - len(lines[i + 1].lstrip())
                        ]
                        if len(next_indent) > len(base_indent):
                            return next_indent
                return base_indent + '    '

        # No Args section, use base indent + 4 spaces
        base_indent = self._get_base_indent(lines)
        return base_indent + '    '

    def _get_base_indent(self, lines: List[str]) -> str:
        r"""Get the base indentation level of the docstring."""
        # Find first non-empty line to determine base indentation
        for line in lines:
            if line.strip() and not line.strip().startswith('"""'):
                return line[: len(line) - len(line.lstrip())]
        return '    '  # Default indentation

    def _extract_param_docs_from_handler(self) -> List[str]:
        r"""Extract parameter documentation from the custom handler's
        docstring.
        """
        if not self.message_handler.__doc__:
            return []

        docs = []
        handler_sig = inspect.signature(self.message_handler)

        # Parse the handler's docstring to find parameter descriptions
        lines = self.message_handler.__doc__.split('\n')
        in_args = False
        param_docs = {}

        for line in lines:
            if (
                'Args:' in line
                or 'Arguments:' in line
                or 'Parameters:' in line
            ):
                in_args = True
                continue
            elif in_args and line.strip():
                # Check if we've reached a new section
                stripped_line = line.lstrip()
                if any(
                    section in stripped_line
                    for section in [
                        'Returns:',
                        'Return:',
                        'Yields:',
                        'Raises:',
                        'Examples:',
                        'Example:',
                        'Note:',
                        'Notes:',
                    ]
                ):
                    # End of Args section
                    break
            elif in_args and ':' in line:
                # Parse parameter documentation
                parts = line.strip().split(':', 1)
                if len(parts) == 2:
                    param_name = parts[0].strip()
                    param_desc = parts[1].strip()
                    # Extract just the parameter name (before any type
                    # annotation)
                    param_name = param_name.split()[0].strip()
                    param_docs[param_name] = param_desc

        # Build documentation for each parameter
        for param_name, param in handler_sig.parameters.items():
            if param_name != 'self':
                # Get type annotation
                annotation = ''
                if param.annotation != inspect.Parameter.empty:
                    if hasattr(param.annotation, '__name__'):
                        annotation = f" ({param.annotation.__name__})"
                    else:
                        annotation = f" ({param.annotation!s})"

                # Check if optional
                optional = (
                    ', optional'
                    if param.default != inspect.Parameter.empty
                    else ''
                )

                # Get description from parsed docs
                desc = param_docs.get(
                    param_name,
                    f"Parameter for {self.message_handler.__name__}",
                )

                docs.append(f"{param_name}{annotation}{optional}: {desc}")

        return docs
