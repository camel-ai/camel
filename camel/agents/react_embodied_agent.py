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
import re
from typing import Dict, List, Optional, Union
import json
import sys
import os

from camel.agents import ChatAgent
from camel.configs import BaseConfig
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.types import ModelType, RoleType, ReasonType
from camel.functions.search_functions import *
from camel.envs import alfworld,bandits,gridworld,highway,metaworld,optimization,poem,reco


class ReactAgent(ChatAgent):
    r"""An agent responsible for reactive reasoning. Model of reactive reasoning:
        - Thought. The agent's explanation on how to answer the question, illustrating what tools to implement.
        - Action. The calling of functions based on the thought. This step includes what the input of the function is and what functions to call.
        - Observation. Summarizing the output of the function.

    Args:
        model_type (ModelType, optional): The type of model to use for the
            agent. (default: :obj: `None`)
        model_config (BaseConfig, optional): The configuration for the model.
            (default: :obj:`None`)
    """
    def __init__(
        self,
        model_type: Optional[ModelType] = None,
        model_config: Optional[BaseConfig] = None,
    ) -> None:
        system_message = BaseMessage(
            role_name="Insight Agent",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You assign roles based on tasks.",
            reason_type=ReasonType.REACT,
        )
        super().__init__(system_message, model_type, model_config)

    def re_act_reasoning(
        self,
        role_descriptions_dict: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Union[List[str], Dict[str, str]]]:
        r"""Derives the conditions and quality from the starting state and the
        target state based on the model of the deductive reasoning and the
        knowledge base. It can optionally consider the roles involved in the
        scenario, which allows tailoring the output more closely to the AI
        agent's environment.

        Args:
            role_descriptions_dict (Optional[Dict[str, str]], optional): The
                descriptions of the roles. (default: :obj:`None`)
            role_descriptions_dict (Optional[Dict[str, str]], optional): A
                dictionary describing the roles involved in the scenario. This
                is optional and can be used to provide a context for the
                CAMEL's role-playing, enabling the generation of more relevant
                and tailored conditions and quality assessments. This could be
                generated using a `RoleAssignmentAgent()` or defined manually
                by the user.

        Returns:
            Dict[str, Union[List[str], Dict[str, str]]]: A dictionary with the
                extracted data from the message. The dictionary contains three
                keys:
                - 'Thought': A list where each key is a condition ID and
                    each value is the corresponding condition text.
                - 'Action': A list of label strings extracted from the message.
                - 'Observation': A string of quality assessment strings extracted
                    from the message.
        """
        self.reset()

        react_instructions = """You are an reactive reasoner. You solve a question answering task with interleaving Thought, Action, Observation steps. The Thought part can reason about the current situation, explain the thinking process, and deciding which tools to implement.
The Action part implements the tool. The observation part collects and summarizes the output of the function called in the Action part. In summary, the response contains three parts  
(1) Thought:\n <BLANK>. Because our thoughts contain {keywords}, we decide to implement the {entity}. 
(2) Action: \n We implement the {entity}. We summarize the output of {entity}.
(3) Observation:  <BLANK>

Here are a few examples regarding the tool of {entity}: 
{role_with_description_prompt}
"""  # noqa: E501

        # write a wrapper beyond the current existing wrappers.
        # After deciding the factor. First present corresponding prompts for llm to brush up.

        react_prompt = react_instructions
        # add the prompts stored in
        idx_dict = ['reco', 'poem', 'optimization', 'bandits']
        for i in range(4):
            prompt_path = os.path.join('./camel/envs/', idx_dict[i], 'prompts.py')
            f = open(prompt_path)
            examples = f.readlines()
            react_examples = TextPrompt(examples)
            react_prompt = react_prompt + react_examples

        # Now create some examples for each task and put them into the prompt
        # For the moment, we only support the tool of an optimization agent. 
        react_optimization_example = """
        Question: Can you find the minimum point of y in terms of x, with the expression y = pow(x,2)? The initial point is 1.
        Thought: Based on the keyword minimum of the function, we could implement the optimization tool agent. 
        Action: We are now implementing the optimization tool agent. 
        Observation: episode 1: x = 1, reward: 1
        episode 2: set x = 0, reward: 0 
        You have reached the minimum!  
        """
        if role_descriptions_dict is not None:
            role_names = role_descriptions_dict.keys()
            role_with_description_prompt = \
                "===== ROLES WITH DESCRIPTIONS =====\n" + "\n".join(
                    f"{role_name}:\n{role_descriptions_dict[role_name]}\n"
                    for role_name in role_names) + "\n\n"
        else:
            role_with_description_prompt = ""

        react_reasoning = react_prompt.format(
            role_with_description_prompt=role_with_description_prompt)

        conditions_and_quality_generation_msg = \
            BaseMessage.make_user_message(role_name="Reactive Reasoner",
                                          content=react_reasoning)

        response = self.step(
            input_message=conditions_and_quality_generation_msg)

        if response.terminated:
            raise RuntimeError("Reasoning failed. Error:\n" +
                               f"{response.info}")
        thought_action: BaseMessage = response.msg
        print(f"Message content:\n{thought_action.content}")

        thought, action = thought_action.content.strip().split('\n')

        # Write a wrapper
        observation = env.step(self, action)

        result: str = response.info
        # Leave the following part in test cases: extracting the conditions from the message and print.

        return thought, action, observation
