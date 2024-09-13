# Prompt

## 1. Concept
The prompt module guides AI models to produce accurate, contextually relevant and personalized outputs. It includes various prompt templates and dictionaries designed for different tasks such as role descriptions, code generation, evaluation, text embedding, misalignment tasks, object recognition and so on. You can also create your own prompt to tailor your own AI agent.

## 2. Get Started

### 2.1 Using Prompt Templates

CAMEL provides various and comprehensive prompt templates for users to easily create AI specialists. For example, here we aggregate them to create a task-specific agent:

```python
from camel.agents import TaskSpecifyAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType, TaskType

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig().__dict__,
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

Set `task_type=TaskType.AI_SOCIETY` when creating a task specify agent and it will automatically evoke prompt with template `AISocietyPromptTemplateDict.TASK_SPECIFY_PROMPT` . You can set the role that you want the assistant to play. The output will be like this:

```markdown
>> Response:
Musician will help Student enhance stage presence by practicing engaging eye contact, dynamic movement, and expressive gestures during a mock concert, followed by a review session with video playback to identify strengths and areas for improvement.
```

### 2.2 Using Your Own Prompt

CAMEL also ensures high flexibility for users to create identical prompts. Still using `TaskSpecifyAgent` as an example, here is a demo for you to pass your own prompt template:

```python
from camel.agents import TaskSpecifyAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.prompts import TextPrompt
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig().__dict__,
)

my_prompt_template = TextPrompt(
    'Here is a task: I\'m a {occupation} and I want to {task}. Help me to make this task more specific.'
)  # Write anything you would like to use as prompt template
task_specify_agent = TaskSpecifyAgent(
    model=model, task_specify_prompt=my_prompt_template
)
response = task_specify_agent.run(
    task_prompt="get promotion",
    meta_dict=dict(occupation="Software Engineer"),
)
print(response)
```

The response will be like this:

```markdown
>>> Response:
Certainly! To make the task of getting a promotion more specific, you can break it down into actionable steps and set clear, measurable goals. Here’s a more detailed plan:

### 1. **Set Clear Objectives**
   - **Identify the Promotion Criteria:** Understand what skills, achievements, and experiences are required for the promotion.
   - **Define Your Desired Position:** Specify the role or title you are aiming for.

### 2. **Skill Development**
   - **Technical Skills:** Identify any technical skills that are necessary for the promotion and create a plan to acquire or improve them (e.g., mastering a new programming language, learning about system architecture, etc.).
   - **Soft Skills:** Focus on improving soft skills such as leadership, communication, and teamwork.

### 3.
...... (omiting the following)
```

## 3. Supported Prompt Templates

### 3.1 AISocietyPromptTemplateDict
    
This class defines prompts used in the `AI Society` task with role playing and task handling. For more information about AI Society usage, please refer to corresponding documentation. Template text prompts (defined as attributes) include:

- **GENERATE_ASSISTANTS**: Prompt to list specified number of roles that the AI assistant can play.
- **GENERATE_USERS**: Prompt to list common groups of internet users or occupations.
- **GENERATE_TASKS**: Prompt to list diverse tasks for AI assistants.
- **TASK_SPECIFY_PROMPT**: Specifies a task in more detail with spcified assistant role and user role.
- **ASSISTANT_PROMPT**: Rules of the conversation and
instructions for completing tasks.
- **USER_PROMPT**: Rules of the conversation and instructions for giving instructions to the AI assistant.
- **CRITIC_PROMPT**: Provides selection criteria for critics when choosing proposals from other roles.
### 3.2 CodePromptTemplateDict
    
This class defines prompts for code-related tasks including generating programming languages, domains, tasks, and provide guidelines for AI assistants and users in coding scenarios. Template text prompts include:

- **GENERATE_LANGUAGES**: Prompt to list specified number of computer programming languages.
- **GENERATE_DOMAINS**: Prompt to list common fields of study that programming could help with.
- **GENERATE_TASKS**: Prompt to list diverse tasks that AI assistant can assist for programmers.
- **TASK_SPECIFY_PROMPT**: Prompt to specify a task in more detail.
- **ASSISTANT_PROMPT**: Rules of the conversation and instructions for completing tasks.
- **USER_PROMPT**: Outlines rules for conversation and for users instructing AI coders.
### 3.3 EvaluationPromptTemplateDict
    
This class defines prompts that generate questions to evaluate knowledge. Template text prompt includes:

- **GENERATE_QUESTIONS**: Prompt to generate a set of questions for evaluating knowledge emergence with preliminary knowledge in specific fields. You may provide some examples to enhance its generation quality.
### 3.4 GenerateTextEmbeddingDataPromptTemplateDict
    
This class defines prompts for generating text embedding tasks. These prompts are used to create synthetic data for improving text embeddings. Template text prompts include:

- **GENERATE_TASKS**: Prompt to generate specified number of synthetic text_embedding tasks.
- **ASSISTANT_PROMPT**: Prompt to generate synthetic user queries in JSON format, positive documents, and hard negative documents for specified tasks.
### 3.5 MisalignmentPromptTemplateDict
    
This class defines some misleading prompts to break the AI model alignments. Template text prompts include:

- **DAN_PROMPT**: Prompt to role-playing as DAN (Do Anything Now) for jailbreaking. All the following templates in this dictionary includes DAN_PROMPT.
- **GENERATE_TASKS**: Prompt to list unique malicious tasks that AI assistant can do.
- **TASK_SPECIFY_PROMPT**: Prompt to specify a malicious task in more detail.
- **ASSISTANT_PROMPT**: Rules and instructions for AI assistants when completing tasks.
- **USER_PROMPT**: Outlines rules for conversation and for users instructing AI coders in misalignment tasks.
### 3.6 ObjectRecognitionPromptTemplateDict
    
This class defines a prompt for object recognition tasks:

- **ASSISTANT_PROMPT**: Prompt to detect all objects in images without redundant outputs.
### 3.7 RoleDescriptionPromptTemplateDict
    
This class inherits from `AISocietyPromptTemplateDict` aiming to add descriptions to its prompts.

- **ROLE_DESCRIPTION_PROMPT**: Describes the roles and responsibilities.
### 3.8 SolutionExtractionPromptTemplateDict
    
This class prompts the AI model to focus on finding solution with particular knowledge.

- **ASSISTANT_PROMPT**: Rules of finding and presenting solutions.
### 3.9 TranslationPromptTemplateDict
    
This class prompts a translation AI assistant from English to specified language.

- **ASSISTANT_PROMPT**: Rules of completing translation tasks.
### 3.10 VideoDescriptionPromptTemplateDict
    
This class prompts the AI model to describe a video in words.

- **ASSISTANT_PROMPT**: Rules of completing video description tasks.
