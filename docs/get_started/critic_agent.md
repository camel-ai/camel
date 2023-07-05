# Introduction to `CriticAgent` class

In this tutorial, we will learn the `CriticAgent` class, which is a subclass of the `ChatAgent` class. The `CriticAgent` class assists in selecting an option based on the input message.The topics covered include:
- Introduction to `CriticAgent` class
- Creating a `CriticAgent` instance
- Using the `CriticAgent` class

## Introduction
The `CriticAgent` class is a subclass of the `ChatAgent` class. The `CriticAgent` class assists in selecting an option based on the input message.

## Creating a `CriticAgent` instance

To create a `CriticAgent` instance, you need to provide the following arguments:
- `system_message`:The system message for the critic agent.
- `model`:(optional) The LLM model to use for generating responses. By default, it is set to `ModelType.GPT_3_5_TURBO`.
- `model_config`:(optional) The configuration for the model. By default, it is set to `None`.
- `message_window_size`:The maximum number of previous messages to include in the context window. If `None`, no windowing is performed.By default, it is set to `6`.
- `retry_attempts`:The number of retry attempts if the critic fails to return a valid option.By default, it is set to `2`.
- `verbose`:(bool) Whether to print the critic's messages. By default, it is set to `False`.
- `logger_color`:The color of the menu options displayed to the user. By default, it is set to `Fore.MAGENTA`.

```python 
from camel.agents import CriticAgent
from camel.messages import BaseMessage
from camel.typing import RoleType

critic_agent = CriticAgent(
    BaseMessage(
        "critic",
        RoleType.CRITIC,
        None,            
        content=("You are a critic who assists in selecting an option "
                "and provides explanations. "
                "Your favorite fruit is Apple. "
                "You always have to choose an option."),
    )
)
```

## Using the `CriticAgent` class

### The `flatten_options` method
Flatten the options to the critic.

```python
messages = [
        BaseMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=dict(),
            content="Apple",
        ),
        BaseMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=dict(),
            content="Banana",
        ),
]
print(critic_agent.flatten_options(messages))
>>> Proposals from user (RoleType.USER). Please choose an option:
Option 1:
Apple

Option 2:
Banana

Please first enter your choice ([1-2]) and then your explanation and comparison: 
```

### The `get_options` method
Get the options selected by the critic.
```python
flatten_options = critic_agent.flatten_options(messages)
input_message = BaseMessage(
    role_name="user",
    role_type=RoleType.USER,
    meta_dict=dict(),
    content=flatten_options,
)
print(critic_agent.options_dict)
>>> {"1": "Apple", "2": "Banana"}
```

### The `parse_critic` method
Parse the critic's message and extract the choics.
```python 
critic_msg = BaseMessage(
        role_name="critic",
        role_type=RoleType.CRITIC,
        meta_dict=dict(),
        content="I choose option 1",
)
print(critic_agent.parse_critic(critic_msg))
>>> "1"
```

### The `reduce_step` method
Performs one step of the conversation by flattening options to the critic, getting the option, and parsing the choice.

```python 
critic_response = critic_agent.reduce_step(messages)
print(critic_response.msg)
>>> BaseMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=dict(),
            content="Apple",
        )
```