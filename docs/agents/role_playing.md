# Creating Your First Agent Society

## Philosophical Bits
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1HU4-sxNWFTs9JOegGbKOBcgHjDfj8FX5?usp=sharing)


> *What magical trick makes us intelligent? The trick is that there is no trick. The power of intelligence stems from our vast diversity, not from any single, perfect principle.*
>
> -- Marvin Minsky, The Society of Mind, p. 308

In this section, we will take a spite of the task-oriented `RolyPlaying()` class. We design this in an instruction-following manner. The essence is that to solve a complex task, you can enable two communicative agents collabratively working together step by step to reach solutions. The main concepts include:
- **Task**: a task can be as simple as an idea, initialized by an inception prompt.
- **AI User**: the agent who is expected to provide instructions.
- **AI Assistant**: the agent who is expected to respond with solutions that fulfills the instructions.


## Quick Start

### Step 0: Preparations

```python
# Import necessary classes
from camel.societies import RolePlaying
from camel.types import TaskType, PredefinedModelType, ModelPlatformType
from camel.models import ModelFactory

# Set the LLM model type and model config
model_platform = ModelPlatformType.OPENAI
model_type = PredefinedModelType.GPT_3_5_TURBO
model_config = ChatGPTConfig(
    temperature=0.8,  # the sampling temperature; the higher the more random
    n=3,  # the no. of completion choices to generate for each input
)

# Create the backend model
model = ModelFactory.create(
    model_platform=model_platform,
    model_type=model_type,
    model_config=model_config)
```

### Step 1: Configure the Role-Playing Session
#### Set the `Task` Arguments
```python
task_kwargs = {
    'task_prompt': 'Develop a plan to TRAVEL TO THE PAST and make changes.',
    'with_task_specify': True,
    'task_specify_agent_kwargs': {'model': model}
}
```

#### Set the `User` Arguments
You may think the user as the `instruction sender`.
```python
user_role_kwargs = {
    'user_role_name': 'an ambitious aspiring TIME TRAVELER',
    'user_agent_kwargs': {'model': model}
}
```

#### Set the `Assistant` Arguments
Again, you may think the assistant as the `instruction executor`.
```python
assistant_role_kwargs = {
    'assistant_role_name': 'the best-ever experimental physicist',
    'assistant_agent_kwargs': {'model': model}
}
```

### Step 2: Kickstart Your Society
Putting them altogether – your role-playing session is ready to go!
```python
society = RolePlaying(
    **task_kwargs,             # The task arguments
    **user_role_kwargs,        # The instruction sender's arguments
    **assistant_role_kwargs,   # The instruction receiver's arguments
)
```

### Step 3: Solving Tasks with Your Society
Hold your bytes. Prior to our travel, let's define a small helper function.
```python
def is_terminated(response):
    """
    Give alerts when the session shuold be terminated.
    """
    if response.terminated:
        role = response.msg.role_type.name
        reason = response.info['termination_reasons']
        print(f'AI {role} terminated due to {reason}')

    return response.terminated
```
Time to chart our course – writing a simple loop for our society to proceed:
```python
def run(society, round_limit: int=10):

    # Get the initial message from the ai assistant to the ai user
    input_msg = society.init_chat()

    # Starting the interactive session
    for _ in range(round_limit):

        # Get the both responses for this round
        assistant_response, user_response = society.step(input_msg)

        # Check the termination condition
        if is_terminated(assistant_response) or is_terminated(user_response):
            break

        # Get the results
        print(f'[AI User] {user_response.msg.content}.\n')
        print(f'[AI Assistant] {assistant_response.msg.content}.\n')

        # Check if the task is end
        if 'CAMEL_TASK_DONE' in user_response.msg.content:
            break

        # Get the input message for the next round
        input_msg = assistant_response.msg

    return None
```
Now let's set our code in motion:
```python
run(society)
```
There you have your two lovely agents working collaboratively together to fulfill your requests. : )
```markdown
>>> [AI User] Instruction: Provide the theoretical framework for creating a stable wormhole or manipulating spacetime for controlled travel to a specific historical era in the past.
>>> [AI Assistant] Solution: To create a theoretical framework for stable wormhole creation or spacetime manipulation for controlled time travel, we can start by considering the principles of general relativity and quantum mechanics.
>>> ... (omitted)
>>> [AI User] <CAMEL_TASK_DONE>.
>>> [AI Assistant] Great! Good luck with your ambitious endeavors in time travel!.
```



## Remarks
We hope you enjoy thie adventure with the two communicative agents. In the following chapters, we will discuss various types of agents, and how we can elicit complex task solving ability for large language models within our framework. Stay tuned.
