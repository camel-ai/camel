# Working with the `ChatAgent` Class

In this tutorial, we will explore the `ChatAgent` class designed for managing conversations of CAMEL Chat Agents. The topics covered include:

1. Introduction to the `ChatAgent` class
2. Creating a `ChatAgent` instance
3. Understanding the properties of the `ChatAgent` class
4. Using the methods of the `ChatAgent` class

## Introduction

The `ChatAgent` class is a central component in the CAMEL chat system. It inherits from the `BaseAgent` class and provides functionality to manage and generate chat conversations using different models.

## Creating a `ChatAgent` Instance

To create a `ChatAgent` instance, you need to provide the following arguments:

- `system_message`: The system message for the chat agent.
- `model`: (optional) The LLM model to use for generating responses.
- `model_config`: (optional) Configuration options for the LLM model.
- `message_window_size`: (optional) The maximum number of previous messages to include in the context window.
- `output_language`: (optional) The language to be output by the agent.
- `function_list`: (optional) List of available `OpenAIFunction`.

Here's an example of creating a `ChatAgent` instance:

```python
from camel.agent import ChatAgent, BaseMessage, ModelType

agent = ChatAgent(
    system_message=BaseMessage(...),
    model=ModelType.GPT_3_5_TURBO,
    message_window_size=5,
    output_language="en"
)
```

## Understanding the Properties of the `ChatAgent` Class

The `ChatAgent` class, designed for managing conversations of CAMEL Chat Agents, encompasses the following properties:

- `orig_sys_message`: An instance of `BaseMessage` representing the original system message for the chat agent.
- `system_message`: An instance of `BaseMessage` denoting the current system message for the chat agent.
- `role_name`: A string that captures the role name extracted from the system message.
- `role_type`: An instance of the `RoleType` enumeration, which identifies the type of role extracted from the system message.
- `output_language`: An optional string that specifies the desired output language for the agent.
- `model`: An instance of `ModelType` representing the LLM model used for generating responses.
- `message_window_size`: An optional integer that dictates the maximum number of previous messages to be included in the context.
- `func_dict`: A dictionary, with keys being strings and values being callable functions, that lists available OpenAIFunctions mapped by their names.
- `model_config`: An instance of `BaseConfig` or its subclass, providing configuration options for the LLM model.
- `model_backend`: An instance of `BaseModelBackend` which is the backend used for the LLM model.
- `model_token_limit`: An integer indicating the token limit for the LLM model.
- `terminated`: A boolean flag that indicates whether the chat session has been terminated.
- `stored_messages`: A list of `ChatRecord` objects representing the stored messages in the chat session.

For instance, after initializing a `ChatAgent` instance, the `role_name` and `role_type` are derived from the provided `system_message`. If no model is explicitly set, the `model` defaults to `ModelType.GPT_3_5_TURBO`.

## Using the Methods of the `ChatAgent` Class

The `ChatAgent` class provides a suite of methods that enable the agent to manage conversations, generate responses, and perform various operations related to chat interactions. Here's an exploration of some key methods:

1. **Performing a Chat Session Step**:
    The `step` method lets you generate a response for a given input message and provides details of the chat session. 
    ```python
    input_msg = BaseMessage(...)
    response = agent.step(input_message=input_msg)
    print(response.output_messages)
    >>> [<BaseMessage content="Generated response">]
    ```

2. **Setting and Getting the System Message**:
    Use the setter and getter methods to update and retrieve the system message of the agent.
    ```python
    # Setting the system message
    agent.system_message = new_system_message

    # Getting the system message
    current_system_message = agent.system_message
    print(current_system_message)
    >>> <BaseMessage content="Your system message">
    ```

3. **Checking Function Calling Capability**:
    The method `is_function_calling_enabled` informs if the OpenAI function calling is enabled for the agent.
    ```python
    is_enabled = agent.is_function_calling_enabled()
    print(is_enabled)
    >>> True
    ```

4. **Setting Output Language**:
    The `set_output_language` method allows you to specify the language for the generated output and retrieve the updated system message.
    ```python
    updated_message = agent.set_output_language("en")
    print(updated_message)
    >>> <BaseMessage content="Your updated system message">
    ```

5. **Retrieving Chat Session Information**:
    Use the `get_info` method to obtain information about the chat session, including ID, usage, termination reasons, and more.
    ```python
    info = agent.get_info(id="12345", usage={}, termination_reasons=[], num_tokens=100, called_funcs=[])
    print(info)
    >>> {"id": "12345", "usage": {}, ...}
    ```

6. **Initializing Stored Messages**:
    The `init_messages` method initializes the stored messages list with the initial system message.
    ```python
    agent.init_messages()
    print(agent.stored_messages)
    >>> [<BaseMessage object>, ...]
    ```

7. **Updating Stored Messages**:
    The `update_messages` method allows you to add a new message to the stored messages and retrieve the updated list.
    ```python
    updated_messages = agent.update_messages(role="user", message=new_message)
    print(updated_messages)
    >>> [<BaseMessage object>, ...]
    ```

8. **Submitting an External Message as an Assistant Response**:
    The `submit_message` method allows you to provide an external message as if it were a response from the chat LLM.
    ```python
    external_message = BaseMessage(...)
    agent.submit_message(external_message)
    ```

9. **Resetting the Agent**:
    The `reset` method allows you to reset the `ChatAgent` to its initial state and also retrieve the stored messages.
    ```python
    stored_messages = agent.reset()
    print(stored_messages)
    >>> [<BaseMessage object>, ...]
    ```

10. **Preprocessing Messages for OpenAI Input**:
    The `preprocess_messages` method truncates the list of messages if needed, converts them to OpenAI's input format, and calculates the token count.
    ```python
    chat_records = [...]
    openai_msgs, tokens = agent.preprocess_messages(messages=chat_records)
    print(tokens)
    >>> 150
    ```

11. **Validating Model's Response**:
    The `validate_model_response` method ensures that the response from the model is in the expected format.
    ```python
    model_response = {...}
    agent.validate_model_response(response=model_response)
    ```

12. **Handling Batch Response from Model**:
    The `handle_batch_response` method processes the batch response from the model and returns the chat messages, finish reasons, and other relevant details.
    ```python
    batch_response = {...}
    messages, reasons, usage, response_id = agent.handle_batch_response(response=batch_response)
    print(messages)
    >>> [<BaseMessage content="Message 1">, <BaseMessage content="Message 2">]
    ```

13. **Handling Stream Response from Model**:
    The `handle_stream_response` method processes the stream response from the model and returns the chat messages, finish reasons, and other relevant details.
    ```python
    stream_response = {...}
    prompt_tokens_count = 100
    messages, reasons, usage, response_id = agent.handle_stream_response(response=stream_response, prompt_tokens=prompt_tokens_count)
    print(messages)
    >>> [<BaseMessage content="Streamed Message 1">, <BaseMessage content="Streamed Message 2">]
    ```

14. **Executing Function Calls Post Model's Response**:
    The `step_function_call` method allows you to execute a specific function using the arguments provided in the model's response.
    ```python
    model_response = {...}
    assist_msg, func_msg, func_record = agent.step_function_call(response=model_response)
    print(assist_msg.func_name)
    >>> "function_name_from_response"
    ```

15. **Getting Token Usage in Stream Mode**:
    The `get_usage_dict` method provides a dictionary detailing the token usage in streaming mode.
    ```python
    output_msgs = [...]
    prompt_tokens_count = 100
    usage = agent.get_usage_dict(output_messages=output_msgs, prompt_tokens=prompt_tokens_count)
    print(usage["total_tokens"])
    >>> 200
    ```

16. **String Representation of ChatAgent**:
    The `__repr__` method returns a string representation of the `ChatAgent` instance.
    ```python
    print(agent)
    >>> ChatAgent(role_name_value, RoleType.VALUE, ModelType.VALUE)
    ```

The `ChatAgent` class is equipped with a suite of 17 methods designed to facilitate smooth interactions in a chat environment. From basic functions like resetting the agent (`reset`) and updating stored messages (`update_messages`), to more complex operations like handling streamed responses from the model (`handle_stream_response`) and executing function calls post model's response (`step_function_call`), the `ChatAgent` ensures comprehensive control over chat sessions. This versatility ensures the `ChatAgent` can effectively manage various scenarios, be it changing the output language (`set_output_language`), validating model responses (`validate_model_response`), or even offering a clear string representation of itself (`__repr__`).

The `ChatAgent` class, part of the CAMEL library, is a robust tool designed for facilitating and managing chat interactions. It leverages an assortment of classes, such as `BaseMessage`, to standardize messages and handle them efficiently. With a plethora of properties like `role_name`, `role_type`, and methods ranging from message handling to complex operations, it stands as a comprehensive solution for chat-based systems. The class not only ensures that messages are processed and stored efficiently but also offers seamless integration with OpenAI's models. With capabilities like function execution based on model responses and built-in validation mechanisms, `ChatAgent` stands out as an indispensable tool for developers venturing into chatbot development and similar applications.