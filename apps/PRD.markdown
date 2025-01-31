# CAMEL Demo Web UI - Product Requirements Document

## Overview
A React-based web interface for demonstrating CAMEL's various modules, enabling users to:
- Interact with multiple model types (DeepSeek, InternLM, Qwen, etc.)
- View agent/mutil-agent responses
- View and copy implementation code
- Learn best practices for integration

## Target Users
- Developers/Researchers/Technical integrating CAMEL into their applications, or trying CAMEL
- Open-source contributors

## 1. Create Your First Agent

### a. Model Management Interface
- **Model Selection**
  - Support for multiple models:
    - DeepSeek
    - InternLM
    - Qwen
    - Future model integrations
  - Quick switch between models

- **Setting Controls**
  - system_message
  - tools
  - message_window_size
  - model-specific configurations (temperature etc..)

- **Status Display**
  - API key validation
  - Current settings
  - Usage metrics (optional)

### b. Interactive Chat Interface

  - Multi-round chatting interface
  - Clear chat option
  - Code syntax highlighting (optional)
  - LaTeX rendering (optional)


### c. Tools Integration
- **Available Tools**
    - [camel/toolkits](https://github.com/camel-ai/camel/tree/master/camel/toolkits)

- **Tool Configuration**
  - Tool-specific settings
  - API key management

- **Tool Usage Interface**
  - Tool selection dropdown
  - Parameter input forms
  - Result visualization
  - Error handling and feedback

- **Example Code**
```python
from camel.agents import ChatAgent
from camel.configs import DeepSeekConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import ArxivToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg ='You are a helpful assistant'

# Set model config
tools = ArxivToolkit().get_tools()
model_config_dict = DeepSeekConfig(
    temperature=0.0,
).as_dict()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEEPSEEK,
    model_type=ModelType.DEEPSEEK_CHAT,
    model_config_dict=model_config_dict,
)

# Set agent
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)
camel_agent.reset()

# Define a user message
usr_msg ="""Search paper 'attention is all you need' for me"""

# Get response information
response = camel_agent.step(usr_msg)

print(response.msg.content)
```


## 2. Create Your Role Playing Session

Role Playing enables multi-agent interactions where agents can take on different roles and collaborate to accomplish tasks.

### a. Additional Configurations Based on 1. Create Your First Agent

- **Task Configuration**
  - `task_prompt`: Define the task for agents to accomplish
  - `output_language`: Specify response language

- **Agent Settings**
  - Assistant Agent
    - Role name
    - Model configuration
    - Tools configuration
  - User Agent
    - Role name
    - Model configuration
  - Optional: Critic Agent for evaluation, Task Agent for task management

### b. Session Management
- Initialize chat session
- Handle agent responses
- Process tool execution results
- Manage conversation flow

- **Example Code**
```python
from typing import List

from colorama import Fore

from camel.agents.chat_agent import FunctionCallingRecord
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.societies import RolePlaying
from camel.toolkits import (
    MathToolkit,
    SearchToolkit,
)
from camel.types import ModelPlatformType, ModelType
from camel.utils import print_text_animated


def main(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    chat_turn_limit=10,
) -> None:
    task_prompt = (
        "Assume now is 2024 in the Gregorian calendar, "
        "estimate the current age of University of Oxford "
        "and then add 10 more years to this age, "
        "and get the current weather of the city where "
        "the University is located."
    )

    user_model_config = ChatGPTConfig(temperature=0.0)

    tools_list = [
        *MathToolkit().get_tools(),
        *SearchToolkit().get_tools(),
    ]
    assistant_model_config = ChatGPTConfig(
        temperature=0.0,
    )

    role_play_session = RolePlaying(
        assistant_role_name="Searcher",
        user_role_name="Professor",
        assistant_agent_kwargs=dict(
            model=ModelFactory.create(
                model_platform=model_platform,
                model_type=model_type,
                model_config_dict=assistant_model_config.as_dict(),
            ),
            tools=tools_list,
        ),
        user_agent_kwargs=dict(
            model=ModelFactory.create(
                model_platform=model_platform,
                model_type=model_type,
                model_config_dict=user_model_config.as_dict(),
            ),
        ),
        task_prompt=task_prompt,
        with_task_specify=False,
    )

    print(
        Fore.GREEN
        + f"AI Assistant sys message:\n{role_play_session.assistant_sys_msg}\n"
    )
    print(
        Fore.BLUE + f"AI User sys message:\n{role_play_session.user_sys_msg}\n"
    )

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
        tool_calls: List[FunctionCallingRecord] = [
            FunctionCallingRecord(**call.as_dict())
            for call in assistant_response.info['tool_calls']
        ]
        for func_record in tool_calls:
            print_text_animated(f"{func_record}")
        print_text_animated(f"{assistant_response.msg.content}\n")

        if "CAMEL_TASK_DONE" in user_response.msg.content:
            break
    
        input_msg = assistant_response.msg


if __name__ == "__main__":
    main()

```


## 3. Create Your Workforce Session

Workforce enables coordinating multiple agents with different capabilities to collaboratively solve complex tasks. Each agent can have its own role, tools, and model configuration. The workforce can include both single agents and role-playing agent pairs for more complex interactions.

### a. Workforce Configuration
- **Workforce Setup**
  - Workforce name and description
  - Task definition and management
  - Agent coordination strategies

- **Agent Management**
  - Add/remove single agents
  - Add/remove role-playing agent pairs
  - Define agent roles and responsibilities
  - Configure agent-specific tools and models

### b. Task Processing Interface
  - Progress monitoring
  - Result aggregation and presentation
  - Error handling and recovery

- **Example Code**
```python
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies import Workforce
from camel.tasks import Task
from camel.toolkits import (
    GoogleMapsToolkit,
    SearchToolkit,
    WeatherToolkit,
)
from camel.types import ModelPlatformType, ModelType

# Set up tools
function_list = [
    *SearchToolkit().get_tools(),
    *WeatherToolkit().get_tools(),
    *GoogleMapsToolkit().get_tools(),
]

# Set up single agents
guide_agent = ChatAgent(
    system_message=BaseMessage.make_assistant_message(
        role_name="tour guide",
        content="You have to lead everyone to have fun",
    )
)

planner_agent = ChatAgent(
    system_message=BaseMessage.make_assistant_message(
        role_name="planner",
        content="Expert at creating detailed tour plans",
    )
)

# Set up role-playing pair configuration
model_platform = ModelPlatformType.DEFAULT
model_type = ModelType.DEFAULT
assistant_role_name = "Searcher"
user_role_name = "Professor"

assistant_agent_kwargs = dict(
    model=ModelFactory.create(
        model_platform=model_platform,
        model_type=model_type,
    ),
    tools=function_list,
)

user_agent_kwargs = dict(
    model=ModelFactory.create(
        model_platform=model_platform,
        model_type=model_type,
    ),
)

# Create and configure workforce with both single agents and role-playing pairs
workforce = Workforce('Travel Planning Team')

# Add role-playing pair
workforce.add_role_playing_worker(
    'Research Team',
    assistant_role_name,
    user_role_name,
    assistant_agent_kwargs,
    user_agent_kwargs,
    max_turns=1,
)

# Add single agents
workforce.add_single_agent_worker(
    'Tour Guide',
    worker=guide_agent,
).add_single_agent_worker(
    'Travel Planner',
    worker=planner_agent,
)

# Define and process task
task = Task(
    content="Research the history of Paris and create a comprehensive tour plan.",
    id='task_001',
)

# Process task through workforce
result = workforce.process_task(task)
print('Task Result:', result.result)
```


## 4. Agentic Synethtic Data Generation

Implemeted by Avery using Gradio (better integrate into huggingface), we can embed this part in our web app or create a jump link.


## 5. Agent with RAG & Graph RAG

### a. RAG (Retrieval-Augmented Generation)

#### Configuration Interface
- **Data Management**
  - Load and process documents
  - Configure embedding model
  - Vector store selection and setup

- **RAG Settings**
  - Customized RAG configuration
  - Retrieval parameters
  - Context window size

#### Agent Integration
- **Single Agent with RAG**
  - Agent configuration with RAG capabilities
  - Query processing and context retrieval
  - Response generation with retrieved context

- **Role-Playing with RAG**
  - Multi-agent setup with RAG
  - Context sharing between agents
  - Task-specific knowledge retrieval

- **Example Code**
https://docs.camel-ai.org/cookbooks/advanced_features/agents_with_rag.html

### b. Graph RAG 

#### Knowledge Graph Setup
  - Database configuration
  - Knowledge graph agent setting
  - Entity and relationship extraction
  - Graph visualization options


- **Example Code**
https://docs.camel-ai.org/cookbooks/advanced_features/agents_with_graph_rag.html


## 6. Agents with Human-in-the-loop

### a. Human Layer Integration
  - HumanLayer API key setup

### b. Tool Approval System
  - Tool execution approval workflow
  - Permission levels and scopes
  - Approval request interface
  - Response handling

### c. Interactive Features
  - Decision point notifications
  - Feedback collection and processing

  - Tool execution request display
  - Context and risk information(optional)
  - Approve/Reject controls
  - History and audit trail(optional)

- **Example Code**
https://docs.camel-ai.org/cookbooks/advanced_features/agents_with_human_in_loop_and_tool_approval.html
