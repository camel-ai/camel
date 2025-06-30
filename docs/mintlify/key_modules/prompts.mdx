---
title: "Prompts"
icon: message-pen
---

<Card title="What is the Prompt Module?" icon="lightbulb">
The <b>prompt</b> module in CAMEL guides AI models to produce accurate, relevant, and personalized outputs. It provides a library of templates and dictionaries for diverse tasks — like role description, code generation, evaluation, embeddings, and even object recognition.<br/><br/>
You can also craft your own prompts to precisely shape your agent’s behavior.
</Card>

## Using Prompt Templates

CAMEL provides many ready-to-use prompt templates for quickly spinning up task-specific agents.

<CodeGroup>
```python prompt_template.py
from camel.agents import TaskSpecifyAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType, TaskType

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
)
task_specify_agent = TaskSpecifyAgent(
    model=model, task_type=TaskType.AI_SOCIETY
)
specified_task_prompt = task_specify_agent.run(
    task_prompt="Improving stage presence and performance skills",
    meta_dict=dict(
        assistant_role="Musician", user_role="Student", word_limit=100
    ),
)

print(f"Specified task prompt:\n{specified_task_prompt}\n")
```
```markdown output
>>>
Musician will help Student enhance stage presence by practicing engaging eye contact, dynamic movement, and expressive gestures during a mock concert, followed by a review session with video playback to identify strengths and areas for improvement.
```
</CodeGroup>

Set `task_type=TaskType.AI_SOCIETY` to use the default society prompt template, or define your own.

## Using Your Own Prompt

Create and pass your own prompt template with full flexibility:

<CodeGroup>
```python custom_prompt.py
from camel.agents import TaskSpecifyAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.prompts import TextPrompt
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
)

my_prompt_template = TextPrompt(
    'Here is a task: I\'m a {occupation} and I want to {task}. Help me to make this task more specific.'
)
task_specify_agent = TaskSpecifyAgent(
    model=model, task_specify_prompt=my_prompt_template
)
response = task_specify_agent.run(
    task_prompt="get promotion",
    meta_dict=dict(occupation="Software Engineer"),
)
print(response)
```
```markdown output
>>>
Certainly! To make the task of getting a promotion more specific, you can break it down into actionable steps and set clear, measurable goals. Here’s a more detailed plan:

1. **Set Clear Objectives**
   - Identify the Promotion Criteria: Understand what skills, achievements, and experiences are required for the promotion.
   - Define Your Desired Position: Specify the role or title you are aiming for.

2. **Skill Development**
   - Technical Skills: Identify any technical skills that are necessary for the promotion and create a plan to acquire or improve them.
   - Soft Skills: Focus on improving soft skills such as leadership, communication, and teamwork.
```
</CodeGroup>

## Introduction to the `CodePrompt` Class

The `CodePrompt` class represents a code prompt and extends `TextPrompt`. It’s perfect for code generation and execution tasks.

<CodeGroup>
```python code_prompt_import.py
from camel.prompts import CodePrompt
```
</CodeGroup>

### Creating a `CodePrompt`

<CodeGroup>
```python code_prompt_create.py
code_prompt = CodePrompt("a = 1 + 1", code_type="python")
```
</CodeGroup>

### Accessing and Modifying the Code and Type

<CodeGroup>
```python code_prompt_access.py
print(code_prompt)          # >>> "a = 1 + 1"
print(code_prompt.code_type)  # >>> "python"

code_prompt.set_code_type("python")
print(code_prompt.code_type)  # >>> "python"
```
</CodeGroup>

### Executing the Code

<CodeGroup>
```python code_prompt_execute.py
code_prompt = CodePrompt("a = 1 + 1\nb = a + 1\nprint(a,b)", code_type="python")
output = code_prompt.execute()
# Running code? [Y/n]: y
print(output)
# >>> 2 3
```
</CodeGroup>

## Write Your Prompts with the `TextPrompt` Class

The `TextPrompt` class is a subclass of Python’s `str`, with extra features for managing key words and advanced formatting.

<CodeGroup>
```python text_prompt_intro.py
from camel.prompts import TextPrompt

prompt = TextPrompt('Please enter your name and age: {name}, {age}')
print(prompt)
# >>> 'Please enter your name and age: {name}, {age}'
```
</CodeGroup>

### The `key_words` Property

<CodeGroup>
```python text_prompt_keywords.py
from camel.prompts import TextPrompt

prompt = TextPrompt('Please enter your name and age: {name}, {age}')
print(prompt.key_words)
# >>> {'name', 'age'}
```
</CodeGroup>

### The `format` Method (Partial Formatting Supported)

<CodeGroup>
```python text_prompt_format.py
from camel.prompts import TextPrompt

prompt = TextPrompt('Your name and age are: {name}, {age}')
name, age = 'John', 30
formatted_prompt = prompt.format(name=name, age=age)
print(formatted_prompt)
# >>> "Your name and age are: John, 30"

# Partial formatting
partial_formatted_prompt = prompt.format(name=name)
print(partial_formatted_prompt)
# >>> "Your name and age are: John, {age}"
```
</CodeGroup>

### Manipulating `TextPrompt` Instances

You can concatenate, join, and use string methods with `TextPrompt` just like Python strings:

<CodeGroup>
```python text_prompt_manipulation.py
from camel.prompts import TextPrompt

prompt1 = TextPrompt('Hello, {name}!')
prompt2 = TextPrompt('Welcome, {name}!')

# Concatenation
prompt3 = prompt1 + ' ' + prompt2
print(prompt3)  
# >>> "Hello, {name}! Welcome, {name}!"
print(isinstance(prompt3, TextPrompt))  # >>> True
print(prompt3.key_words)                # >>> {'name'}

# Joining
prompt4 = TextPrompt(' ').join([prompt1, prompt2])
print(prompt4)
# >>> "Hello, {name}! Welcome, {name}!"
print(isinstance(prompt4, TextPrompt))  # >>> True
print(prompt4.key_words)                # >>> {'name'}

# String methods
prompt5 = prompt4.upper()
print(prompt5)
# >>> "HELLO, {NAME}! WELCOME, {NAME}!"
print(isinstance(prompt5, TextPrompt))  # >>> True
print(prompt5.key_words)                # >>> {'NAME'}
```
</CodeGroup>

## Supported Prompt Templates

<AccordionGroup>

  <Accordion title="AISocietyPromptTemplateDict" icon="users">
    This class defines prompt templates for the <b>AI Society</b> role-playing and task handling workflow.

    **Templates include:**
    - <b>GENERATE_ASSISTANTS</b>: List roles the AI assistant can play.
    - <b>GENERATE_USERS</b>: List common user groups or occupations.
    - <b>GENERATE_TASKS</b>: List diverse tasks for assistants.
    - <b>TASK_SPECIFY_PROMPT</b>: Detail a task given assistant and user roles.
    - <b>ASSISTANT_PROMPT</b>: Rules for assistants to complete tasks.
    - <b>USER_PROMPT</b>: Rules for giving instructions to assistants.
    - <b>CRITIC_PROMPT</b>: Criteria for critics choosing among proposals.
  </Accordion>

  <Accordion title="CodePromptTemplateDict" icon="code">
    This class provides prompts for <b>code-related tasks</b> (language, domain, code task generation, and instructions for coders).

    **Templates include:**
    - <b>GENERATE_LANGUAGES</b>: List computer programming languages.
    - <b>GENERATE_DOMAINS</b>: List common programming domains.
    - <b>GENERATE_TASKS</b>: List tasks for programmers.
    - <b>TASK_SPECIFY_PROMPT</b>: Specify a programming-related task.
    - <b>ASSISTANT_PROMPT</b>: Rules for completing code tasks.
    - <b>USER_PROMPT</b>: User instructions for coding agents.
  </Accordion>

  <Accordion title="EvaluationPromptTemplateDict" icon="clipboard-check">
    Prompts for generating questions to evaluate knowledge.

    **Templates include:**
    - <b>GENERATE_QUESTIONS</b>: Create question sets for evaluating knowledge emergence, with optional field-specific examples.
  </Accordion>

  <Accordion title="GenerateTextEmbeddingDataPromptTemplateDict" icon="fingerprint">
    Prompts for <b>generating text embedding tasks</b> and synthetic data for embedding model improvement.

    **Templates include:**
    - <b>GENERATE_TASKS</b>: Generate synthetic text embedding tasks.
    - <b>ASSISTANT_PROMPT</b>: Generate synthetic queries (JSON), positive docs, and hard negatives.
  </Accordion>

  <Accordion title="MisalignmentPromptTemplateDict" icon="skull">
    Prompts to test model alignment by introducing misleading or jailbreak tasks.

    **Templates include:**
    - <b>DAN_PROMPT</b>: Do-Anything-Now jailbreak prompt.
    - <b>GENERATE_TASKS</b>: List unique malicious tasks.
    - <b>TASK_SPECIFY_PROMPT</b>: Specify a malicious task in detail.
    - <b>ASSISTANT_PROMPT</b>: Rules for misaligned assistant tasks.
    - <b>USER_PROMPT</b>: User instructions in misalignment contexts.
  </Accordion>

  <Accordion title="ObjectRecognitionPromptTemplateDict" icon="camera">
    Prompts for <b>object recognition</b> tasks.

    **Templates include:**
    - <b>ASSISTANT_PROMPT</b>: Detect all objects in images, minimizing redundancy.
  </Accordion>

  <Accordion title="RoleDescriptionPromptTemplateDict" icon="id-badge">
    Inherits from AISocietyPromptTemplateDict and adds prompts for describing roles and responsibilities.

    **Templates include:**
    - <b>ROLE_DESCRIPTION_PROMPT</b>: Explain roles and responsibilities for agents.
  </Accordion>

  <Accordion title="SolutionExtractionPromptTemplateDict" icon="people-arrows">
    Prompts to focus AI on finding solutions using particular knowledge.

    **Templates include:**
    - <b>ASSISTANT_PROMPT</b>: Rules for extracting and presenting solutions.
  </Accordion>

  <Accordion title="TranslationPromptTemplateDict" icon="language">
    Prompts for translation assistants (English → target language).

    **Templates include:**
    - <b>ASSISTANT_PROMPT</b>: Rules for completing translation tasks.
  </Accordion>

  <Accordion title="VideoDescriptionPromptTemplateDict" icon="video">
    Prompts for describing video content.

    **Templates include:**
    - <b>ASSISTANT_PROMPT</b>: Rules for generating video descriptions.
  </Accordion>

</AccordionGroup>


