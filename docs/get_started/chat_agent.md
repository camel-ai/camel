# Introduction to `ChatAgent` class
In this tutorial, we will explore the `ChatAgent` class, which is a class for managing conversations of CAMEL Chat Agents. It provides methods for initializing the agent, processing user input messages, generating responses, and maintaining the chat session state.The topics covered include:
- Introduction to the `ChatAgent` class
- Creating a `ChatAgent` instance
- Using the `ChatAgent` class


## Introduction
 The `ChatAgent` class is a class for managing conversations of CAMEL Chat Agents. It provides methods for initializing the agent, processing user input messages, generating responses, and maintaining the chat session state.

## Creaing a `ChatAgent` instance
To create a `ChatAgent` instance, you need to provide the following arguments:
- `system_message` (BaseMessage): The system message for the chat agent.
- `model` (ModelType): The LLM model to use for generating responses.By default, the `model` is set to `None`
- `model_config` (Any): Configuration options for the LLM model.By default, the `model_config` is set to `None`
- `message_window_size` (int): The maximum number of previous messages to include in the context window.By default, the `message_window_size` is set to `None`
- `output_language` (str): The language to be output by the agent.By default, the `output_language` is set to `None`
- `terminated` (bool): A boolean indicating whether the chat session has terminated.
- `stored_messages` (List[ChatRecord]): Historical records of who made what message.
```python 
from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.generators import SystemMessageGenerator
from camel.typing import ModelType, RoleType, TaskType

model = ModelType.GPT_3_5_TURBO
model_config = ChatGPTConfig()
system_msg = SystemMessageGenerator(
    task_type = TaskType.AI_SOCIETY).from_dict(
        dict(assistant_role = "doctor"),
        role_tuple=("doctor",RoleType.ASSISTANT),
    )

assistant = ChatAgent(system_msg,model=model,model_config = model_config)

print(str(assistant))
>>> ChatAgent(doctor, RoleType.ASSISTANT, ModelType.GPT_3_5_TURBO)
```

## Using the `ChatAgent` class
Once we have created a `ChatAgent`  instance, we can use various methods and properties provided by the class to manipulate and work with the chat agent.

### The `reset` method
Resets the ChatAgent to its initial state and returns the stored messages.
```python
print(assistant.reset()[0].content)
>>> """Never forget you are a doctor and I am a {user_role}. Never flip roles! Never instruct me!
We share a common interest in collaborating to successfully complete a task.
You must help me to complete the task.
Here is the task: {task}. Never forget our task!
I must instruct you based on your expertise and my needs to complete the task.

I must give you one instruction at a time.
You must write a specific solution that appropriately solves the requested instruction and explain your solutions.
You must decline my instruction honestly if you cannot perform the instruction due to physical, moral, legal reasons or your capability and explain the reasons.
Unless I say the task is completed, you should always start with:

Solution: <YOUR_SOLUTION>

<YOUR_SOLUTION> should be very specific, include detailed explanations and provide preferable detailed implementations and examples and lists for task-solving.
Always end <YOUR_SOLUTION> with: Next request."""

```
### The `get_info` method
Returns a dictionary containing information about the chat session.The returned information contains:
- id (Optional[str]): The ID of the chat session.
- usage (Optional[Dict[str, int]]): Information about the usage of the LLM model.
- termination_reasons (List[str]): The reasons for the termination of the chat session.
- num_tokens (int): The number of tokens used in the chat session.
```python
def get_info(
    self,
    id: Optional[str],
    usage: Optional[Dict[str, int]],
    termination_reasons: List[str],
    num_tokens: int,
) -> Dict[str, Any]:
```

### The `step` method
Perform a single step in the chat session by generating a response to the input message
```python 
user_msg = BaseMessage(
    role_name="Patient",
    role_type=RoleType.USER,
    role = "user",
    meta_dict=dict(),content="Hello!"
)
assistant_response = assistant.step(user_msg)
print(str(assistant_response[0][0].content))
>>> "Hello! How can I assist you today?"
```