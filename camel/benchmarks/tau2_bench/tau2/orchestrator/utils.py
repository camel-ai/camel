from tau2.data_model.message import AssistantMessage, Message, ToolMessage


def is_valid_environment_message(msg: Message) -> bool:
    """
    Check if the message is valid to the environment.
    """
    return isinstance(msg, ToolMessage) or (
        isinstance(msg, AssistantMessage) and msg.is_tool_call()
    )
