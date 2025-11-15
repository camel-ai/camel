import ast
import re
from typing import Any

from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage


def parse_action_string(action: str, requestor: str = "assistant") -> AssistantMessage:
    """
    Parse an action string and return the appropriate message object with tool calls or content.

    This function handles multiple formats of action strings:
    1. JSON-formatted tool calls (valid ToolCall JSON)
    2. Functional tool calls (e.g., "function_name(arg1=value1, arg2=value2)")
    3. Plain text content (non-tool call actions)

    The function automatically detects the format and creates the appropriate message type
    (AssistantMessage or UserMessage) based on the requestor parameter.

    Args:
        action: The action string to parse. Can be:
            - JSON string representing a ToolCall object
            - Functional call string like "function_name(arg1=value1, arg2=value2)"
            - Plain text content for non-tool actions
        requestor: The role of the message sender. Must be either "assistant" (default)
                  or "user". Determines whether to return AssistantMessage or UserMessage.

    Returns:
        AssistantMessage or UserMessage: A message object containing either:
            - Tool calls (if the action was a valid tool call format)
            - Text content (if the action was plain text)
            - The original action string is preserved in the raw_data field

    Raises:
        ValueError: If the action string is empty or cannot be parsed

    Examples:
        >>> # JSON tool call
        >>> parse_action_string('{"name": "search", "arguments": {"query": "flights"}}')
        AssistantMessage(role="assistant", content=None, tool_calls=[ToolCall(...)], raw_data="...")

        >>> # Functional tool call
        >>> parse_action_string("search_flights(origin='NYC', destination='LAX')")
        AssistantMessage(role="assistant", content=None, tool_calls=[ToolCall(...)], raw_data="...")

        >>> # Plain text content
        >>> parse_action_string("Hello, how can I help you?")
        AssistantMessage(role="assistant", content="Hello, how can I help you?", tool_calls=None, raw_data="...")

        >>> # User message
        >>> parse_action_string("I need help", requestor="user")
        UserMessage(role="user", content="I need help", tool_calls=None, raw_data="...")
    """
    if requestor == "user":
        MessageClass = UserMessage
    else:
        MessageClass = AssistantMessage

    original_action = action
    action = action.strip()
    # Check for empty action after stripping
    if not action:
        raise ValueError("Action cannot be empty")

    # Check if it is a tool call JSON string
    try:
        tool_call = ToolCall.model_validate_json(action)
        message = MessageClass(
            role=requestor,
            content=None,
            tool_calls=[tool_call],
            raw_data={"action": original_action},
        )
        return message
    except Exception:
        pass

    # Check if it is a functional tool call
    if is_functional_tool_call(action):
        try:
            tool_call = parse_functional_tool_call(action, requestor)
            message = MessageClass(
                role=requestor,
                content=None,
                tool_calls=[tool_call],
                raw_data={"action": original_action},
            )
            return message
        except Exception:
            # If functional parsing fails, treat as plain text
            pass

    # Always return a plain text message if previous attempts fail
    message = MessageClass(
        role=requestor,
        content=original_action,
        tool_calls=None,
        raw_data={"action": original_action},
    )
    return message


def parse_functional_tool_call(
    functional_call: str, requestor: str = "assistant"
) -> ToolCall:
    """
    Parse a functional form tool call into a ToolCall object.

    Args:
        functional_call: String in format "function_name(arg1=value1, arg2=value2, ...)"
        requestor: The requestor of the tool call ("user" or "assistant")

    Returns:
        ToolCall object with parsed name and arguments

    Raises:
        ValueError: If the functional call format is invalid
        SyntaxError: If the arguments cannot be parsed as valid Python

    Examples:
        >>> parse_functional_tool_call("search_flights(origin='NYC', destination='LAX')")
        ToolCall(name="search_flights", arguments={"origin": "NYC", "destination": "LAX"})

        >>> parse_functional_tool_call("book_ticket(flight_id=123, passenger_name='John Doe')")
        ToolCall(name="book_ticket", arguments={"flight_id": 123, "passenger_name": "John Doe"})
    """
    if not functional_call.strip():
        raise ValueError("Functional call cannot be empty")

    # Remove any leading/trailing whitespace
    functional_call = functional_call.strip()

    # Match function name and arguments
    # Pattern: function_name(arguments)
    match = re.match(r"^(\w+)\s*\((.*)\)$", functional_call)
    if not match:
        raise ValueError(
            f"Invalid functional call format: {functional_call}. Expected format: function_name(arg1=value1, arg2=value2, ...)"
        )

    function_name = match.group(1)
    arguments_str = match.group(2).strip()

    # Parse arguments
    arguments = {}

    if arguments_str:  # Only parse if there are arguments
        try:
            # Create a safe AST to parse the arguments
            # We'll parse it as a function call with keyword arguments
            safe_code = f"dummy_function({arguments_str})"
            tree = ast.parse(safe_code)

            # Extract keyword arguments from the function call
            if isinstance(tree.body[0], ast.Expr) and isinstance(
                tree.body[0].value, ast.Call
            ):
                call_node = tree.body[0].value
                for keyword in call_node.keywords:
                    key = keyword.arg
                    value = _evaluate_ast_node(keyword.value)
                    arguments[key] = value
            else:
                raise ValueError(f"Could not parse arguments: {arguments_str}")

        except (SyntaxError, ValueError) as e:
            raise ValueError(f"Invalid arguments format: {arguments_str}. Error: {e}")

    return ToolCall(name=function_name, arguments=arguments, requestor=requestor)


def _evaluate_ast_node(node: ast.AST) -> Any:
    """
    Safely evaluate an AST node to extract its value.

    Args:
        node: AST node to evaluate

    Returns:
        The evaluated value (string, number, boolean, list, dict, etc.)

    Raises:
        ValueError: If the node type is not supported
    """
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.UnaryOp):
        # Handle unary operations like -1, +2, etc.
        operand = _evaluate_ast_node(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +operand
        elif isinstance(node.op, ast.USub):
            return -operand
        else:
            raise ValueError(f"Unsupported unary operation: {type(node.op).__name__}")
    elif isinstance(node, ast.List):
        return [_evaluate_ast_node(item) for item in node.elts]
    elif isinstance(node, ast.Dict):
        keys = [_evaluate_ast_node(key) for key in node.keys]
        values = [_evaluate_ast_node(value) for value in node.values]
        return dict(zip(keys, values))
    elif isinstance(node, ast.Tuple):
        return tuple(_evaluate_ast_node(item) for item in node.elts)
    elif isinstance(node, ast.Name):
        # Handle special names like True, False, None
        if node.id == "True":
            return True
        elif node.id == "False":
            return False
        elif node.id == "None":
            return None
        else:
            # For other names, treat as string (common in tool calls)
            return node.id
    else:
        raise ValueError(f"Unsupported AST node type: {type(node).__name__}")


def is_functional_tool_call(text: str) -> bool:
    """
    Check if a string looks like a functional tool call.

    Args:
        text: String to check

    Returns:
        True if the string matches the functional tool call pattern

    Examples:
        >>> is_functional_tool_call("search_flights(origin='NYC')")
        True
        >>> is_functional_tool_call("Hello, how can I help you?")
        False
    """
    if not text or not text.strip():
        return False

    text = text.strip()
    # Pattern: word followed by parentheses
    return bool(re.match(r"^\w+\s*\(.*\)$", text))


def to_functional_format(tool_call: ToolCall) -> str:
    """
    Convert a ToolCall object to functional format string.

    Args:
        tool_call: ToolCall object to convert

    Returns:
        String in functional format: "function_name(arg1=value1, arg2=value2, ...)"

    Examples:
        >>> tool_call = ToolCall(name="search_flights", arguments={"origin": "NYC", "destination": "LAX"})
        >>> to_functional_format(tool_call)
        "search_flights(origin='NYC', destination='LAX')"

        >>> tool_call = ToolCall(name="refresh", arguments={})
        >>> to_functional_format(tool_call)
        "refresh()"
    """
    if not tool_call.name:
        raise ValueError("ToolCall must have a name")

    # Start with function name and opening parenthesis
    result = f"{tool_call.name}("

    # Add arguments if any
    if tool_call.arguments:
        arg_pairs = []
        # Sort arguments by key for consistent output
        for key in sorted(tool_call.arguments.keys()):
            value = tool_call.arguments[key]
            # Format the value appropriately
            if isinstance(value, str):
                # Escape single quotes in strings
                escaped_value = value.replace("'", "\\'")
                arg_pairs.append(f"{key}='{escaped_value}'")
            elif isinstance(value, (int, float, bool)) or value is None:
                # Numbers, booleans, and None can be used directly
                arg_pairs.append(f"{key}={value}")
            elif isinstance(value, (list, tuple, dict)):
                # For complex types, use repr() to get proper Python representation
                arg_pairs.append(f"{key}={repr(value)}")
            else:
                # For other types, use repr() as fallback
                arg_pairs.append(f"{key}={repr(value)}")

        result += ", ".join(arg_pairs)

    # Close parenthesis
    result += ")"

    return result
