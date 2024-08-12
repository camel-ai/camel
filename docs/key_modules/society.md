# Society
## 1. Concept
The society module is one of the core modules of CAMEL. By simulating the information exchange process, this module studies the social behaviors among agents. 

Currently, the society module aims to enable agents to collaborate autonomously toward completing tasks while keeping consistent with human intentions and requiring minimal human intervention. It includes two frameworks: Babyagi-Playing and Role-Playing, which are used to plan the interaction behaviors of agents to achieve research objectives.

Taking Role-Playing as an example, this framework was designed in an instruction-following manner. These roles independently undertake the responsibilities of executing and planning tasks, respectively. The dialogue is continuously advanced through a turn-taking mechanism, thereby collaborating to complete tasks. The main concepts include:

Task: a task can be as simple as an idea, initialized by an inception prompt.

AI User: the agent who is expected to provide instructions.

AI Assistant: the agent who is expected to respond with solutions that fulfill the instructions.

### 2. Types

## 2.1 Babyagi-Playing
Babyagi is framework from "Task-driven Autonomous Agent"

## 2.2 Role-Playing

Role-Playing is a unique cooperative agent framework of CAMEL. Through this framework, agents in CAMEL overcome numerous challenges, such as *role flipping*, *assistant repeats instructions*, *flake replies*, *infinite loop of messages*, and *conversation termination conditions.*

When using Role-Playing framework in Camel, predefined prompts are used to create unique initial settings for different agents. For example, if the user wants to initialize a assistant agent, the agent will be initialized with the following prompt.

- Never forget you are a <ASSISTANT_ROLE> and I am a <USER_ROLE>. This assigns the chosen role to the assistant agent and provides it with information about the user’s role.
- Never flip roles! Never instruct me! This prevents agents from flipping roles. In some cases, we have observed the assistant and the user switching roles, where the assistant suddenly takes control and instructs the user, and the user follows those instructions.
- You must decline my instruction honestly if you cannot perform the instruction due to physical, moral, legal reasons or your capability and explain the reasons. This prohibits the agent from producing harmful, false, illegal, and misleading information.
- Unless I say the task is completed, you should always start with: Solution: <YOUR_SOLUTION>. <YOUR_SOLUTION> should be specific, and provide preferable implementations and examples for task-solving. This encourages the assistant to always responds in a consistent format, avoiding any deviation from the structure of the conversation, and preventing vague or incomplete responses, which we refer to as flake responses, such as "I will do something".
- Always end your solution with: Next request. This ensures that the assistant keeps the conversation going by requesting a new instruction to solve.

### Role-Playing Attributes

| Attribute | Type | Description |
| --- | --- | --- |
| assistant_role_name | str | The name of the role played by the assistant. |
| user_role_name | str | The name of the role played by the user. |
| critic_role_name | str | The name of the role played by the critic. |
| task_prompt | str | A prompt for the task to be performed. |
| with_task_specify | bool | Whether to use a task specify agent. |
|  with_task_planner | bool | Whether to use a task planner agent. |
| with_critic_in_the_loop | bool | Whether to include a critic in the loop. |
| critic_criteria | str | Critic criteria for the critic agent. |
| model | BaseModelBackend | The model backend to use for generating responses.  |
| task_type | TaskType | The type of task to perform. |
| assistant_agent_kwargs | Dict | Additional arguments to pass to the assistant agent. |
| user_agent_kwargs | Dict | Additional arguments to pass to the user agent. |
| task_specify_agent_kwargs | Dict | Additional arguments to pass to the task specify agent. |
| task_planner_agent_kwargs | Dict | Additional arguments to pass to the task planner agent. |
| critic_kwargs | Dict | Additional arguments to pass to the critic. |
| sys_msg_generator_kwargs | Dict | Additional arguments to pass to the system message generator. |
| extend_sys_msg_meta_dicts | List[Dict] | A list of dicts to extend the system message meta dicts with. |
| extend_task_specify_meta_dict | Dict | A dict to extend the task specify meta dict with. |
| output_language | str | The language to be output by the agents. |

### Init_chat Function
Initializes the chat by resetting both of the assistant and user agents. Returns an initial message for the role-playing session.  
```python
def init_chat(self, init_msg_content: Optional[str] = None) -> BaseMessage:
        self.assistant_agent.reset()
        self.user_agent.reset()
        default_init_msg_content = (
            "Now start to give me instructions one by one. "
            "Only reply with Instruction and Input."
        )
        if init_msg_content is None:
            init_msg_content = default_init_msg_content
        # Initialize a message sent by the assistant
        init_msg = BaseMessage.make_assistant_message(
            role_name=self.assistant_sys_msg.role_name,
            content=init_msg_content,
        )

        return init_msg
```

### Step Function
Advances the conversation by taking a message from the assistant, processing it using the user agent, and then processing the resulting message using the assistant agent. 

Returns a tuple containing the resulting assistant message, whether the assistant agent terminated the conversation, and any additional assistant information, as well as
a tuple containing the resulting user message, whether the user agent terminated the conversation, and any additional user information.
```python
def step(
        self,
        assistant_msg: BaseMessage,
    ) -> Tuple[ChatAgentResponse, ChatAgentResponse]:
        user_response = self.user_agent.step(assistant_msg)
        if user_response.terminated or user_response.msgs is None:
            return (
                ChatAgentResponse([], False, {}),
                ChatAgentResponse(
                    [], user_response.terminated, user_response.info
                ),
            )
        user_msg = self._reduce_message_options(user_response.msgs)
        self.user_agent.record_message(user_msg)

        assistant_response = self.assistant_agent.step(user_msg)
        if assistant_response.terminated or assistant_response.msgs is None:
            return (
                ChatAgentResponse(
                    [], assistant_response.terminated, assistant_response.info
                ),
                ChatAgentResponse([user_msg], False, user_response.info),
            )
        assistant_msg = self._reduce_message_options(assistant_response.msgs)
        self.assistant_agent.record_message(assistant_msg)

        return (
            ChatAgentResponse(
                [assistant_msg],
                assistant_response.terminated,
                assistant_response.info,
            ),
            ChatAgentResponse(
                [user_msg], user_response.terminated, user_response.info
            ),
        )
```

## 3. Get Started

### 3.1. Using Role-playing

```python
from colorama import Fore

from camel.societies import RolePlaying
from camel.utils import print_text_animated

def main(model=None, chat_turn_limit=50) -> None:
# initial the role-playing session on developing a trading bot task with default model (`GPT_4O_MINI`)
    task_prompt = "Develop a trading bot for the stock market"
    role_play_session = RolePlaying(
        assistant_role_name="Python Programmer",
        assistant_agent_kwargs=dict(model=model),
        user_role_name="Stock Trader",
        user_agent_kwargs=dict(model=model),
        task_prompt=task_prompt,
        with_task_specify=True,
        task_specify_agent_kwargs=dict(model=model),
    )

# Output initial message with different colors.
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

# Output response step by step with different colors.
# Keep output until detect the terminate content or reach the loop limit.
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

        print_text_animated(
            Fore.BLUE + f"AI User:\n\n{user_response.msg.content}\n"
        )
        print_text_animated(
            Fore.GREEN + "AI Assistant:\n\n"
            f"{assistant_response.msg.content}\n"
        )

        if "CAMEL_TASK_DONE" in user_response.msg.content:
            break

        input_msg = assistant_response.msg

if __name__ == "__main__":
    main()
```

### Summary

In the future, we hope to expand this module to realize complex social behaviors among multi-agents, such as interaction, trust building, competition and cooperation, and conflict resolution.