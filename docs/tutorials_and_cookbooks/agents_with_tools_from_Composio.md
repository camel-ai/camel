# 🐫 Agents with Tools from Composio

[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1x2FYThMPtQXLzKZAhf_Ry-oeU6oPygdm?authuser=1#scrollTo=6c1kqMDxDodN)


## In this notebook, we demonstrate the usage of CAMEL `ChatAgent` and `RolePlaying` with Tools from Composio, allowing agents to seamlessly interact with external applications.

*Goal: Star a repository on GitHub with natural language & CAMEL Agent*

## Install Packages & Connect a Tool
Ensure you have the necessary packages installed and connect your GitHub account to allow your CAMEL agents to utilize GitHub functionalities.
```python
import composio
```

Login to Composio
```bash
composio login
```

Connect your Github account (this is a shell command, so it should be run in your terminal or with '!' prefix in a Jupyter Notebook)
```bash
composio add github
```

Check all different apps which you can connect with

```bash
composio apps
```

## Prepare your environment by initializing necessary imports from CAMEL & Composio.

```python
from typing import List

from colorama import Fore
from composio_camel import Action, ComposioToolSet

from camel.agents.chat_agent import FunctionCallingRecord
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.societies import RolePlaying
from camel.types import ModelPlatformType, ModelType
from camel.utils import print_text_animated
```

## Let's run CAMEL agents with tools from Composio!

Set your task
```python
task_prompt = (
    "I have created a new Github Repo,"
    "Please star my github repository: camel-ai/camel"
)
```

Set Toolset
```python
composio_toolset = ComposioToolSet()

tools = composio_toolset.get_actions(
    actions=[Action.GITHUB_ACTIVITY_STAR_REPO_FOR_AUTHENTICATED_USER]
)
```

Set models for user agent and assistant agent, give tool to the assistant
```python 
assistant_agent_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_3_5_TURBO,
    model_config_dict=ChatGPTConfig().as_dict(),
)

user_agent_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_3_5_TURBO,
    model_config_dict=ChatGPTConfig().as_dict(),
)
```

Set RolePlaying session
```python 
role_play_session = RolePlaying(
    assistant_role_name="Developer",
    user_role_name="CAMEL User",
    assistant_agent_kwargs=dict(
        model=assistant_agent_model,
        tools=tools,
    ),
    user_agent_kwargs=dict(
        model=user_agent_model,
    ),
    task_prompt=task_prompt,
    with_task_specify=False,
)
```

Print the system message and task prompt
```python 
print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
print(
    Fore.CYAN
    + "Specified task prompt:"
    + f"\n{role_play_session.specified_task_prompt}\n"
)
print(Fore.RED + f"Final task prompt:\n{role_play_session.task_prompt}\n")
```

```markdown
>>> 
AI Assistant sys message:
Original task prompt:
I have created a new Github Repo,Please star my github repository: camel-ai/camel

Specified task prompt:
None

Final task prompt:
I have created a new Github Repo,Please star my github repository: camel-ai/camel
```

Set terminate rule and print the chat message
```python
n = 0
input_msg = role_play_session.init_chat()
while n < 50:
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
    tool_calls: List[FunctionCallingRecord] = assistant_response.info[
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
AI User:

Instruction: Visit the Github repository I created.
Input: None


AI Assistant:

Solution: To visit the Github repository you created, you can simply open a web browser and go to the following URL: https://github.com/camel-ai/camel

Next request.


AI User:

Instruction: Click on the "Star" button on the Github repository page.
Input: None


AI Assistant:

Function Execution: github_activity_star_repo_for_authenticated_user
	Args: {'owner': 'camel-ai', 'repo': 'camel'}
	Result: {'execution_details': {'executed': True}, 'response_data': ''}

Solution: I have successfully starred your Github repository "camel-ai/camel".

Next request.


AI User:

<CAMEL_TASK_DONE>


AI Assistant:

Great! The task is completed. If you have any more tasks or need further assistance in the future, feel free to ask. Have a wonderful day!
```