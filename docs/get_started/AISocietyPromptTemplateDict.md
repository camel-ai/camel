# Introduction to `AISocietyPromptTemplateDict` class

In this tutorial, we will learn the `AISocietyPromptTemplateDict` class, which is a dictionary containing text prompts used in the `AI Society` task. These prompts provide instructions and guidelines for conducting conversations in the AI Society context.The topics covered include:
- Introduction to `AISocietyPromptTemplateDict` class
- Creating a `AISocietyPromptTemplateDict` instance

## Introduction
The `AISocietyPromptTemplateDict` class is a dictionary containing text prompts used in the `AI Society` task. These prompts provide instructions and guidelines for conducting conversations in the AI Society context.

## Creating a `AISocietyPromptTemplateDict` instance

To create a `AISocietyPromptTemplateDict` instance, you need to provide the following arguments:
- `GENERATE_ASSISTANTS` (TextPrompt): A prompt to list different roles that the AI assistant can play.
- `GENERATE_USERS` (TextPrompt): A prompt to list common groups of internet users or occupations.
- `GENERATE_TASKS` (TextPrompt): A prompt to list diverse tasks that the AI assistant can assist AI user with.
- `TASK_SPECIFY_PROMPT` (TextPrompt): A prompt to specify a task in more detail.
- `ASSISTANT_PROMPT` (TextPrompt): A system prompt for the AI assistant that outlines the rules of the conversation and provides instructions for completing tasks.
- `USER_PROMPT` (TextPrompt): A system prompt for the AI user that outlines the rules of the conversation and provides instructions for giving instructions to the AI assistant.
  
```python 
from camel.prompts import AISocietyPromptTemplateDict

template_dict = AISocietyPromptTemplateDict()
```



