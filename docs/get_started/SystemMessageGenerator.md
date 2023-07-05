# Introduction to `SystemMessageGenerator` class

In this tutorial, we will `SystemMessageGenerator` class.The topics covered include:
- Introduce `SystemMessageGenerator` class
- Creating a `SystemMessageGenerator` instance
- Use the `SystemMessageGenerator` class

## Introduce `SystemMessageGenerator` class 
It's a class used for generating system messages for different roles in a conversation. The system messages provide prompts and instructions to guide the conversation.
## Creating a `SystemMessageGenerator` instance

To create a `SystemMessageGenerator` instance, you need to provide the following arguments:
- `task_type`:(TaskType, optional): The task type.By default, it is set to `TaskType.AI_SOCIETY`.
- `sys_prompts`:(optional) The prompts of the system messages for each role type. By default, it is set to `None`.
- `sys_msg_dict_keys`:(optional) The set of keys of the meta dictionary used to fill the prompts. By default, it is set to `None`.

```python 
from camel.generators import (
    AISocietyTaskPromptGenerator,
    RoleNameGenerator,
    SystemMessageGenerator,
)
from camel.typing import RoleType, TaskType

sys_msg_generator = SystemMessageGenerator(task_type=TaskType.AI_SOCIETY)
```

## Use the `SystemMessageGenerator` class

### The `from_dict` method
Generates a system message from a dictionary.

```python
sys_msg_generator.from_dict(dict(
    assistant_role="doctor"),
    role_tuple=("doctor", RoleType.ASSISTANT)
)
```

### The `from_dicts` method
Generates a list of system messages from a list of dictionaries.

```python
 sys_msg_generator.from_dicts([dict(
    assistant_role="doctor", user_role="doctor")] * 2,
    role_tuples=[("chatbot", RoleType.ASSISTANT),("doctor", RoleType.USER)],
    )
```
