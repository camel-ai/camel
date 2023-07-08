# Introduction to `TaskSpecifyAgent` class

In this tutorial, we will learn the `TextSpecifyAgent` class, which is a subclass of the `ChatAgent` class. The `TaskSpecifyAgent` class is designed to specify a given task prompt by prompting the user to provide more details.The topics covered include:
- Introduction to `TaskSpecifyAgent` class
- Creating a `TaskSpecifyAgent` instance
- Using the `TaskSpecifyAgent` class

## Introduction
The `TaskSpecifyAgent` class is a subclass of the `ChatAgent` class. The `TaskSpecifyAgent` class is designed to specify a given task prompt by prompting the user to provide more details.

## Creating a `TaskSpecifyAgent` instance

To create a `TaskSpecifyAgent` instance, you need to provide the following arguments:
- `model`:(optional) the type of model to use for the agent. By default, it is set to `ModelType.GPT_3_5_TURBO`.
- `task_type`: The type of task for which to generate a prompt.By default, it is set to`TaskType.AI_SOCIETY`.
- `model_config`:(optional) The configuration for the model. By default, it is set to `None`.
- `task_specify_prompt`(optional):The prompt for specifying the task. By default, it is set to `None`.
- `word_limit`:The word limit for the task prompt.By default, it is set to `50`.
- `output_language`:(str, optional) The language to be output by the agent.By default, it is set to `None`.

```python 
model = ModelType.GPT_3_5_TURBO
task_specify_agent = TaskSpecifyAgent(
    model_config=ChatGPTConfig(temperature=1.0), 
    model=model
)
```

## Using the `TaskSpecifyAgent` class

### The `step` method
Generate subtasks based on the input task prompt.

```python
model = ModelType.GPT_3_5_TURBO
original_task_prompt = "Improving stage presence and performance skills"
print(f"Original task prompt:\n{original_task_prompt}\n")
>>> '''Original task prompt:
Improving stage presence and performance skills'''
task_specify_agent = TaskSpecifyAgent(
    model_config=ChatGPTConfig(temperature=1.0), 
    model=model
)
specified_task_prompt = task_specify_agent.step(
    original_task_prompt, 
    meta_dict=dict(
        assistant_role="Musician",
        user_role="Student"))
print(f"Specified task prompt:\n{specified_task_prompt}\n")
>>> '''Specified task prompt:
Musician will help Student improve stage presence and performance skills by creating a unique persona for each song. They will focus on enhancing physical expressions, body movements, and gestures that complement the music, transforming Student into a captivating performer who effortlessly connects with the audience.
'''
```

