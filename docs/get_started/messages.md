# Working with the `BaseMessage` Class

In this tutorial, we will explore the `BaseMessage` class. The topics covered include:

1. Introduction to the `BaseMessage` class.
2. Creating a `BaseMessage` instance.
3. Understanding the properties of the `BaseMessage` class.
4. Using the methods of the `BaseMessage` class.

## Introduction

The `BaseMessage` class is the base class for message objects used in the CAMEL chat system. It is designed to provide a consistent structure for the messages in the system and allow for easy conversion between different message types.

## Creating a `BaseMessage` Instance

To create a `BaseMessage` instance, you need to provide the following arguments:

- `role_name`: The name of the user or assistant role.
- `role_type`: The type of role, either `RoleType.ASSISTANT` or `RoleType.USER`.
- `content`: The content of the message.
- `sender`: Optional. The sender of the message.
- `receiver`: Optional. The receiver of the message.
- `meta_dict`: Optional. A metadata dictionary for the message.
- `message_type`: The type of message, default is `MessageType.DEFAULT`.
- `subject`: Optional. The subject of the message.
- `reply_with`: Optional. The message this is replying with.
- `in_reply_to`: Optional. The message this is in reply to.
- `envelope`: Optional. Envelope containing time sent and received.
- `language`: Optional. The language of the message, default is "en".
- `ontology`: Optional. Ontology related to the message.
- `protocol`: Optional. Protocol related to the message.

Here's an example of creating a `BaseMessage` instance:

```python
from camel.messages import BaseMessage, Content
from camel.types import RoleType

message = BaseMessage(
    role_name="test_user",
    role_type=RoleType.USER,
    content=Content(
        text="test content",
        image_url="test_image_url",
        video_url="test_video_url",
    ),
)
```

Additionally, the `BaseMessage` class provides class methods to easily create user and assistant agent messages:

1. Creating a user agent message:

    ```python
    from camel.messages import BaseMessage, Content

    user_message = BaseMessage.make_user_message(
        role_name="user_name", 
        content=Content(
            text="test content",
            image_url="test_image_url",
            video_url="test_video_url",
        ),
    )
    ```

2. Creating an assistant agent message:

    ```python
    from camel.messages import BaseMessage, Content
    
    assistant_message = BaseMessage.make_assistant_message(
        role_name="assistant_name",
    content=Content(
        text="test content",
        image_url="test_image_url",
        video_url="test_video_url",
    ),
    )
    ```

## Using the Methods of the `BaseMessage` Class

The `BaseMessage` class offers several methods:

1. Creating a new instance with updated content:

    ```python
    new_content = Content(text="new test content")
    new_message = message.create_new_instance(new_content)
    print(isinstance(new_message, BaseMessage))
    >>> True
    ```

2. Adding two `BaseMessage` instances together:

    ```python
    other_message = BaseMessage(
        role_name="another_user",
        role_type=RoleType.USER,
        content=Content(text="additional content")
    )
    combined_message = message + other_message
    print(combined_message.content.text)
    >>> ['test content', 'additional content']
    ```

3. Multiplying a `BaseMessage` instance:

    ```python
    multiplied_message = message * 2
    print(multiplied_message.content.text)
    >>> ['test content', 'test content']
    ```

4. Getting the length of the `BaseMessage` content:

    ```python
    length = len(message)
    print(length)
    >>> 3
    ```

5. Checking if an item is in the `BaseMessage` content:

    ```python
    contains = "test content" in message
    print(contains)
    >>> True
    ```

6. Extracting text and code prompts:

    ```python
    text_prompts, code_prompts = message.extract_text_and_code_prompts()
    print(text_prompts)
    >>> ['test content']
    print(code_prompts)
    >>> []
    ```

7. Converting to an `OpenAIMessage` object:

    ```python
    from camel.types import OpenAIBackendRole
    openai_message = message.to_openai_message(role_at_backend=OpenAIBackendRole.USER)
    ```

8. Converting to an `OpenAISystemMessage` object:

    ```python
    openai_system_message = message.to_openai_system_message()
    ```

9. Converting to an `OpenAIUserMessage` object:

    ```python
    openai_user_message = message.to_openai_user_message()
    ```

10. Converting to an `OpenAIAssistantMessage` object:

    ```python
    openai_assistant_message = message.to_openai_assistant_message()
    ```

11. Converting to a dictionary:

    ```python
    message_dict = message.to_dict()
    ```

These methods allow you to convert a `BaseMessage` instance into different message types depending on your needs.

In this session, we introduced the `BaseMessage` class and its conversion to different types of messages. These components play essential roles in the CAMEL chat system, facilitating the creation, management, and interpretation of messages with clarity.