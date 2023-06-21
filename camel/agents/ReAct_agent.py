# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from typing import Any, Dict, List, Optional, Tuple

from colorama import Fore
import re 

from camel.agents import ChatAgent, BaseToolAgent
from camel.agents.chat_agent import ChatAgentResponse
from camel.messages import ChatMessage, SystemMessage
from camel.typing import ModelType
from camel.utils import print_text_animated


REACT_PROMPT_INSTRUCT = """
For each time of running, you should firstly give a thought about what action to be taken next for solving the target task, and then give an action to be executed.

You should use Thought to describe your thoughts about your plan to obtain information related to the target task.
And you should use Action to indicate what actions should be done, and then return.
You do not need to output any observation! The observations will be obtained by the external tool executing the action you selected and be provided to you.
When there are multiple search-related actions available, consider using others when one search engine fails.

Your available actions are:

Finish[<argument>]
- input <argument>: any value to be returned
- This action finishes this task and returns any value specified by <argument>

"""

REACT_PROMPT_EXAMPLE = """
Remember: For each time of running, you should return after you output an action!

Here are is an example session (this example is only for presentation and works only if the available actions include "Search")
Task: Answer the question: What is the capital of France?
Thought: I should look up France on Wikipedia
Action: Search[France]

At this point you should return. And you will be called again with this:

Observation: France is a country. The capital is Paris.

You then output:

Thought: From the observation, the capital of France is Paris.
Action: Finish[Paris]
"""

# Regular verifier of Action statements
ACTION_RE = re.compile('^Action: *')

# Color settings for logging
TASK_COLOR = Fore.LIGHTYELLOW_EX
THOUGHT_COLOR = Fore.LIGHTCYAN_EX
ACTION_COLOR = Fore.LIGHTRED_EX
OBSERVE_COLOR = Fore.LIGHTGREEN_EX


def parse_action(act_str):
    # example act_str: Search[entity]
    action = act_str.split('[')[0]
    action_input = act_str[:-1].split('[')[1]
    return action, action_input


class ReActAgent(ChatAgent):
    r"""Class for managing conversions of a CAMEL agent following ReAct pattern.

    Args:
        system_message (SystemMessage): The system message for the chat agent.
        model (ModelType, optional): The LLM model to use for generating
            responses. (default :obj:`ModelType.GPT_4`)
        model_config (Any, optional): Configuration options for the LLM model.
            (default: :obj:`None`)
        message_window_size (int, optional): The maximum number of previous
            messages to include in the context window. If `None`, no windowing
            is performed. (default: :obj:`None`)
        action_space (Dict[Any], optional): The action space for the ReAct
            agent. (default: :obj:`None`)
        verbose (bool, optional): Whether to print the critic's messages.
    """

    def __init__(
        self,
        system_message: SystemMessage,
        model: ModelType = ModelType.GPT_4,
        model_config: Optional[Any] = None,
        message_window_size: Optional[int] = None,
        action_space: Dict[str, BaseToolAgent] = None,
        verbose: bool = False,
    ) -> None:
        self.action_space = action_space

        action_space_prompt = self.get_action_space_prompt()
        init_prompt = '\n'.join([
            REACT_PROMPT_INSTRUCT,
            action_space_prompt,
            REACT_PROMPT_EXAMPLE,
        ])
        system_message.content = init_prompt
        
        self.verbose = verbose
        super().__init__(
            system_message=system_message,
            model=model,
            model_config=model_config,
            message_window_size=message_window_size,
        )


    def get_action_space_prompt(self) -> str:
        r"""Returns the action space prompt.

        Returns:
            str: The action space prompt.
        """
        tool_agents = set()
        for agent in self.action_space.values():
            tool_agents.add(agent)

        return "\n".join(agent.description for agent in tool_agents)
    
    def parse_thought_and_action(self, 
                                response: ChatAgentResponse) -> Tuple[str,str]:
        response_msg = response.msg.content
        contents = [a.split(':')[-1].strip() for a in response_msg.split('\n')]
        return contents[0], contents[1]


    def step(
        self,
        input_message: ChatMessage,
        max_turns: int = 10,
    ) -> Tuple[ChatMessage, bool, Dict[str, Any]]:
        r"""Performs a step in the conversation.

        Args:
            input_message (ChatMessage): The input message, 
                                        **which should specify a task to do**

        Returns:
            Tuple[ChatMessage, bool, Dict[str, Any]]: A tuple
                containing the output messages, termination status, and
                additional information.
        """
        response = super().step(input_message)

        if response.msgs is None or len(response.msgs) == 0:
            raise RuntimeError("Got None output messages.")
        if response.terminated:
            raise RuntimeError(f"{self.__class__.__name__} step failed.")
        
        if self.verbose:
            # print_text_animated(TASK_COLOR + f"> Task: {input_message.content}")
            print(TASK_COLOR + f"> Task: {input_message.content}")

        i = 0
        content = input_message.content 
        while i < max_turns:
            i += 1
            content += f"\n{response.msg.content}"

            # Add the thought and action into the agent's conversation history
            self.update_messages(
                ChatMessage(role_name=self.role_name, role_type=self.role_type,
                            meta_dict=self.system_message.meta_dict,
                            role=self.system_message.role,
                            content=response.msg.content)
            )

            # Parse the new output containing a pair of Thought and Action
            thought, action = self.parse_thought_and_action(response)
            action, action_input = parse_action(action) 
            
            if self.verbose:
                # print_text_animated(THOUGHT_COLOR + f"> Thought: {thought}")
                # print_text_animated(ACTION_COLOR + f"> Action: {action}[{action_input}]")
                print(THOUGHT_COLOR + f"> Thought: {thought}")
                print(ACTION_COLOR + f"> Action: {action}[{action_input}]")
                
            # Terminate
            if action == 'Finish':
                break

            # operation argument is for ToolAgent providing multiple actions
            obs = str(self.action_space[action].step(action_input, operation=action))
            if self.verbose:
                # print_text_animated(OBSERVE_COLOR + f"> Observation: {obs}")
                print(OBSERVE_COLOR + f"> Observation: {obs}")
                
            # TODO not sure which type of message should be used
            obs = ChatMessage(
                role_type=self.role_type,
                role_name=self.system_message.role_name,
                meta_dict=self.system_message.meta_dict,
                role=self.system_message.role,
                content=obs,
            )
            response = super().step(obs)


        # TODO: Handle failed cases
        # TODO: Note the output emits all previous messages which has already been added into the
        # Agent's conversation history in the previous loop. RolePlaying should not update the conversation
        # history by the output again.
        finish_msg = ChatMessage(role_name=self.role_name, role_type=self.role_type,
                                meta_dict=input_message.meta_dict, role=input_message.role,
                                content=content)
        return finish_msg, response.terminated, response.info
