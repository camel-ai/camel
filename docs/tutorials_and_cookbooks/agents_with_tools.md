# 🐫 Agents with Tools

[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1DMtHu4v2GqfjgvC9H4jkp49Bv1Fkd3DH?authuser=1#scrollTo=ssX_map8c6mx)


## In this notebook, we demonstrate the usage of CAMEL Tools with ChatAgent and RolePlaying.

2 main parts included:
- Using Tools Integrated by CAMEL
- Customize Your Own Tools


Import CAMEL modules, for the tool part we will take search tool as one example, other tools are commented out.
```python
from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.toolkits import (
    SEARCH_FUNCS,
    # MAP_FUNCS,
    # MATH_FUNCS,
    # TWITTER_FUNCS,
    # WEATHER_FUNCS,
    # RETRIEVAL_FUNCS,
    # TWITTER_FUNCS,
    # SLACK_FUNCS,
)
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
```

Let's customize one tool, take the simple math calactor as one example, when you define your own function, please make sure the argument name and docstring is clear, Agent will try to understand what this function can do and when to use the function based on the function information you provided.
```python
def add(a: int, b: int) -> int:
    r"""Adds two numbers.

    Args:
        a (int): The first number to be added.
        b (int): The second number to be added.

    Returns:
        integer: The sum of the two numbers.
    """
    return a + b

def sub(a: int, b: int) -> int:
    r"""Do subtraction between two numbers.

    Args:
        a (int): The minuend in subtraction.
        b (int): The subtrahend in subtraction.

    Returns:
        integer: The result of subtracting :obj:`b` from :obj:`a`.
    """
    return a - b
```


Add these 2 customized functions as CAMEL's OpenAIFunction list
```python
from camel.functions.openai_function import OpenAIFunction


MATH_FUNCS: list[OpenAIFunction] = [
    OpenAIFunction(func) for func in [add, sub]
]
```

Add the tool from CAMEL and defined by yourself to the tool list
```python
tool_list = [*SEARCH_FUNCS, *MATH_FUNCS]
```

Set the ChatAgent able to call the tool
```python
# Set the backend mode, this model should support tool calling
model=ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_3_5_TURBO,
    model_config_dict=ChatGPTConfig(
        temperature=0.0,
    ).as_dict(),
)

# Set message for the assistant
assistant_sys_msg = BaseMessage.make_assistant_message(
    role_name="Search Agent",
    content= """You are a helpful assistant to do search task."""
)

# Set the config parameter for the model
assistant_model_config = ChatGPTConfig(
    temperature=0.0,
)

# Set the agent
agent = ChatAgent(
    assistant_sys_msg,
    model=model,
    tools=tool_list
)
```

Let's define two test prompt for the agent to run
```python
# Set prompt for the search task
prompt_search = ("""When was University of Oxford set up""")
# Set prompt for the calculation task
prompt_calculate = ("""Assume now is 2024 in the Gregorian calendar, University of Oxford was set up in 1096, estimate the current age of University of Oxford""")

# Convert the two prompt as message that can be accepted by the Agent
user_msg_search = BaseMessage.make_user_message(role_name="User", content=prompt_search)
user_msg_calculate = BaseMessage.make_user_message(role_name="User", content=prompt_calculate)

# Get response
assistant_response_search = agent.step(user_msg_search)
assistant_response_calculate = agent.step(user_msg_calculate)
```

Let's see how did the agent use the tool for the 2 tasks
```python
print(assistant_response_search.info['tool_calls'])
```

```markdown
>>> 
[FunctionCallingRecord(func_name='search_wiki', args={'entity': 'University of Oxford'}, result="The University of Oxford is a collegiate research university in Oxford, United Kingdom. There is evidence of teaching as early as 1096, making it the oldest university in the English-speaking world and the world's second-oldest university in continuous operation. It grew rapidly from 1167, when Henry II banned English students from attending the University of Paris. After disputes between students and Oxford townsfolk in 1209, some academics fled north-east to Cambridge where they established what became the University of Cambridge. The two English ancient universities share many common features and are jointly referred to as Oxbridge.")]
```

```python
print(assistant_response_calculate.info['tool_calls'])
```

```markdown
>>> 
[FunctionCallingRecord(func_name='sub', args={'a': 2024, 'b': 1096}, result=928)]
```

Now the single agent has the ability to use tool, let set one small AI society, the society would include one user agent and one assistant agent, the assistant agent is the one we just set can use tool.
```python
from camel.societies import RolePlaying
from camel.agents.chat_agent import FunctionCallingRecord
from camel.utils import print_text_animated
from colorama import Fore

# Set a task
task_prompt=("Assume now is 2024 in the Gregorian calendar, "
        "estimate the current age of University of Oxford "
        "and then add 10 more years to this age.")

# Set role playing
role_play_session = RolePlaying(
    assistant_role_name="Searcher",
    user_role_name="Professor",
    assistant_agent_kwargs=dict(
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_3_5_TURBO,
            model_config_dict=assistant_model_config.as_dict(),
        ),
        tools=tool_list,
    ),
    user_agent_kwargs=dict(
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_3_5_TURBO,
            model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
        ),
    ),
    task_prompt=task_prompt,
    with_task_specify=False,
)

# Set the limit for the chat turn
chat_turn_limit=10

print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
print(
    Fore.CYAN
    + "Specified task prompt:"
    + f"\n{role_play_session.specified_task_prompt}\n"
)
print(Fore.RED + f"Final task prompt:\n{role_play_session.task_prompt}\n")

n = 0
input_msg = role_play_session.init_chat()
while n < chat_turn_limit:
    n += 1
    assistant_response, user_response = role_play_session.step(input_msg)

    if assistant_response.terminated:
        print(
            Fore.GREEN
            + (
                "AI Assistant terminated. Reason: "
                f"{assistant_response.info['termination_reasons']}."
            )
        )
        break
    if user_response.terminated:
        print(
            Fore.GREEN
            + (
                "AI User terminated. "
                f"Reason: {user_response.info['termination_reasons']}."
            )
        )
        break

    # Print output from the user
    print_text_animated(
        Fore.BLUE + f"AI User:\n\n{user_response.msg.content}\n"
    )

    # Print output from the assistant, including any function
    # execution information
    print_text_animated(Fore.GREEN + "AI Assistant:")
    tool_calls: list[FunctionCallingRecord] = assistant_response.info[
        'tool_calls'
    ]
    for func_record in tool_calls:
        print_text_animated(f"{func_record}")
    print_text_animated(f"{assistant_response.msg.content}\n")

    if "CAMEL_TASK_DONE" in user_response.msg.content:
        break

    input_msg = assistant_response.msg
```

```markdown
>>>
Original task prompt:
Assume now is 2024 in the Gregorian calendar, estimate the current age of University of Oxford and then add 10 more years to this age.

Specified task prompt:
None

Final task prompt:
Assume now is 2024 in the Gregorian calendar, estimate the current age of University of Oxford and then add 10 more years to this age.

AI User:

Instruction: Provide the founding year of the University of Oxford.
Input: None


AI Assistant:

Function Execution: search_wiki
	Args: {'entity': 'University of Oxford'}
	Result: The University of Oxford is a collegiate research university in Oxford, United Kingdom. There is evidence of teaching as early as 1096, making it the oldest university in the English-speaking world and the world's second-oldest university in continuous operation. It grew rapidly from 1167, when Henry II banned English students from attending the University of Paris. After disputes between students and Oxford townsfolk in 1209, some academics fled north-east to Cambridge where they established what became the University of Cambridge. The two English ancient universities share many common features and are jointly referred to as Oxbridge.

Solution: The University of Oxford has evidence of teaching as early as 1096, making it the oldest university in the English-speaking world. Therefore, the founding year of the University of Oxford is considered to be around 1096.

Next request.


AI User:

Instruction: Calculate the current age of the University of Oxford in 2024.
Input: None


AI Assistant:

Function Execution: sub
	Args: {'a': 2024, 'b': 1096}
	Result: 928

Solution: The current age of the University of Oxford in 2024 is 928 years.

Next request.


AI User:

Instruction: Add 10 years to the current age of the University of Oxford.
Input: None


AI Assistant:

Function Execution: add
	Args: {'a': 928, 'b': 10}
	Result: 938

Solution: Adding 10 years to the current age of the University of Oxford, the estimated age of the University of Oxford in 2034 would be 938 years.

Next request.


AI User:

<CAMEL_TASK_DONE>


AI Assistant:

Task completed.
```