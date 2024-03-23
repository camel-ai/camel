# Working with the `ChatAgent` Class

In this tutorial, we will explore the `ChatAgent` class designed for managing conversations of CAMEL Chat Agents. The topics covered include:

1. Introduction to the `ChatAgent` class
2. Creating a `ChatAgent` instance
3. Understanding the properties of the `ChatAgent` class
4. Using the methods of the `ChatAgent` class

## Introduction

The `ChatAgent` class is an advanced component of the CAMEL chat system, designed to facilitate interactive conversations. As a subclass of `BaseAgent`, it integrates a language model with optional configurations and memory management to produce dynamic, context-aware chat interactions.

## Creating a `ChatAgent` Instance

When initializing a `ChatAgent`, the following parameters can be configured:

- `system_message`: A mandatory message object that initiates the chat agent's conversation flow.
- `model_type` (optional): Selects the LLM model type for response generation, with a default set to `ModelType.GPT_3_5_TURBO`.
- `model_config` (optional): Defines custom configurations for the chosen LLM model.
- `memory` (optional): Manages the state and history of conversations. Defaults to `ChatHistoryMemory` if not specified.
- `message_window_size` (optional): Controls the number of past messages to consider for context.
- `token_limit` (optional): Sets a cap on the number of tokens to include in the context, with auto-pruning for over-limit scenarios.
- `output_language` (optional): Specifies the desired output language for the agent's responses.
- `function_list` (optional): Lists the `OpenAIFunction` functions available for the chat agent to use.
- `response_terminators` (optional): Provides a list of `ResponseTerminator` objects that determine the end of a chat agent's response.


Here's an example of creating a `ChatAgent` instance:

```python
from camel.agent import ChatAgent, BaseMessage, ModelType, ChatHistoryMemory, ChatGPTConfig

agent = ChatAgent(
    system_message=BaseMessage(...),
    model_type=ModelType.GPT_3_5_TURBO,  # Corrected from `model` to `model_type`
    message_window_size=5,
    output_language="en",
    memory=ChatHistoryMemory(...),  # Assuming you want to show an example of passing a memory
    model_config=ChatGPTConfig(...)  # Assuming you want to show an example of passing a model config
    # You can also include examples of function_list and response_terminators if needed
)
```

## Using the Methods of the `ChatAgent` Class

The `ChatAgent` class offers a variety of methods for comprehensive conversation management within the CAMEL Chat framework. Below, we delve into the functionalities of several essential methods:

1. **Conducting a Chat Step**:
    The `step` method progresses the chat by responding to an input message, returning a structured response that includes any output messages, a termination flag, and session details.
    ```python
    input_msg = BaseMessage(...)
    chat_response = agent.step(input_message=input_msg)
    print(chat_response.output_messages)
    if chat_response.terminated:
        print("Chat session has ended.")
    print(chat_response.info)
    ```

2. **Accessing and Modifying the System Message**:
    Utilize the getter and setter methods for the `system_message` to manage the agent's current system message.
    ```python
    # Updating the system message
    agent.system_message = BaseMessage(...)

    # Retrieving the system message
    current_system_message = agent.system_message
    print(current_system_message)
    >>> <BaseMessage content="Current system message">
    ```

3. **Updating Agent Memory**:
    The `update_memory` method incorporates new messages into the agent's memory.
    ```python
    agent.update_memory(BaseMessage(...), OpenAIBackendRole.USER)
    ```

4. **Getting Session Information**:
    The `get_info` method compiles information about the chat session into a dictionary.
    ```python
    session_info = agent.get_info(
        id="session123",
        usage={"calls": 10, "tokens": 500},
        termination_reasons=["max_turns_reached"],
        num_tokens=500,
        called_funcs=[FunctionCallingRecord(...)]
    )
    print(session_info)
    >>> {"id": "session123", "usage": {...}, "termination_reasons": [...], "num_tokens": 500, "called_functions": [...]}
    ```

5. **Initializing Stored Messages**:
    The `init_messages` method sets up the initial state of the agent's memory with the system message.
    ```python
    agent.init_messages()
    ```

6. **Recording a Message**:
    With the `record_message` method, an external message can be added to the agent's memory, simulating a response from the agent.
    ```python
    external_msg = BaseMessage(...)
    agent.record_message(external_msg)
    ```

7. **Setting the Output Language**:
    The `set_output_language` method adjusts the language for the system message output.
    ```python
    updated_message = agent.set_output_language("es")
    print(updated_message)
    >>> <BaseMessage content="Your system message in Spanish">
    ```

8. **Resetting the Agent**:
   The `reset` method restores the `ChatAgent` to its initial state and retrieves stored messages.
   ```python
   stored_messages = agent.reset()
   print(stored_messages)
   >>> [<BaseMessage content="Previous messages">]
   ```

9. **Handling Batch Responses**:
    The `handle_batch_response` method processes responses from the model that are received in batch format.
    ```python
    response = ChatCompletion(...)
    output_messages, finish_reasons, usage, response_id = agent.handle_batch_response(response)
    ```

10. **Handling Stream Responses**:
    The `handle_stream_response` method deals with responses from the model that are received in a streaming manner.
    ```python
    response = Stream(...)
    prompt_tokens = 100  # Example token count for the input prompt
    output_messages, finish_reasons, usage_dict, response_id = agent.handle_stream_response(response, prompt_tokens)
    ```

11. **Handling Token Exceeding Scenario**:
    The `step_token_exceed` method provides a way to handle scenarios where the token limit is exceeded during response generation.
    ```python
    num_tokens = 1500  # Example token count that exceeded the limit
    termination_reason = "max_tokens_exceeded"
    chat_response = agent.step_token_exceed(num_tokens, [], termination_reason)
    if chat_response.terminated:
        print("Chat session terminated due to token limit.")
    print(chat_response.info)
    ```

12. **Executing Function Calls**:
    The `step_function_call` method is invoked to perform function calls based on the model's response.
    ```python
    response = ChatCompletion(...)
    assistant_message, function_result_message, function_record = agent.step_function_call(response)
    ```

13. **Calculating Usage Metrics**:
    The `get_usage_dict` method compiles usage statistics, particularly useful when streaming responses from the model.
    ```python
    output_messages = [...]  # Assume a list of BaseMessage instances
    prompt_tokens = 100  # Example token count for the input prompt
    usage_metrics = agent.get_usage_dict(output_messages, prompt_tokens)
    print(usage_metrics)
    ```

14. **String Representation of the Agent**:
    The `__repr__` method provides a human-readable representation of the `ChatAgent` instance, useful for debugging and logging.
    ```python
    print(agent)
    >>> ChatAgent(role_name, role_type, model_type)
    ```

The `ChatAgent` class, integral to the CAMEL library, is a sophisticated tool designed for orchestrating and managing conversational interactions. It incorporates a variety of methods, extending from fundamental functionalities like resetting the agent's state (`reset`) and updating memory (`update_memory`), to handling advanced scenarios such as processing streamed responses (`handle_stream_response`) and executing function calls after receiving model responses (`step_function_call`).

Equipped with 14 distinct methods, the `ChatAgent` offers comprehensive control over chat sessions. It is adept at managing various scenarios, including changing the output language (`set_output_language`), and providing a clear representation of its state (`__repr__`). Leveraging classes like `BaseMessage` for message standardization, the `ChatAgent` not only processes and stores messages efficiently but also seamlessly integrates with advanced models. With its capability to execute functions based on model responses and in-built mechanisms for session management, `ChatAgent` is an indispensable asset for developers in the realm of chatbot development and similar applications.
