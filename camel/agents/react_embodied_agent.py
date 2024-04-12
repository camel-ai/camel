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
import camel.llfbench as gym
import random
from camel.agents import ChatAgent
from camel.configs import BaseConfig
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.types import ModelType, RoleType, ReasonType
#from camel.functions.search_functions import *
from camel.envs import bandits, optimization, poem


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
        # idx_dict = ['reco', 'poem', 'optimization', 'bandits']
        # for i in range(4):
        #     prompt_path = os.path.join('./camel/envs/', idx_dict[i], 'prompts.py')
        #     f = open(prompt_path)
        #     examples = f.readlines()
        #     react_examples = TextPrompt(examples)
        #     react_prompt = react_prompt + react_examples

        # Now create some examples for each task and put them into the prompt
        # For the moment, we only support the tool agents included in llf-bench.
        # We implement a two-step language model, where the first steps decide what tool agent in llf-bench to use. The second
        # step implements the tool agent in llf-bench, noticing that it is a language-based reinforcement learning model.
        react_optimization_example = """
        ========Optimization Tool Agent ===============
        Question: I would like to give you an optimization task. 
        Thought: Based on the keyword optimization, we could implement the optimization tool agent with limited information. 
        Question: I would like to minimize a function without knowing its the exact expression. 
        Thought: Based on the keyword optimization, we could implement the optimization tool agent with limited information. 
        Question: I would like to find a minimizer of a function without knowing its the exact expression. 
        Thought: Based on the keyword optimization, we could implement the optimization tool agent with limited information. 
        """

        react_bandit_example = """
        ========Bandit Problem Tool Agent ===============
        Question: I would like to do a bandit problem.
        Thought: Based on the keywords in your request, we could implement the bandit tool agent.
        Question: I want to apply a multi-armed bandit problem. 
        Thought: Based on the keywords in your request, we could implement the bandit tool agent.
        """

        react_poem_example = """
        ========Poem Composing Tool Agent ===============
        Question: I would like to write a poem.
        Thought: Based on the keywords in your request, we could implement the poem composing tool agent. 
        Question: I would like to write something that has rhymes.
        Thought: Based on the keywords in your request, we could implement the poem composing tool agent.
        """

        react_prompt = react_prompt + react_poem_example + react_bandit_example + react_optimization_example
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
        ENVIRONMENTS_OPTIMIZATION = (
            'Booth',
            'McCormick',
            'Rosenbrock',
            'SixHumpCamel',
        )

        ENVIRONMENTS_BANDIT = (
            'BanditTenArmedRandomFixed-v0',
            'BanditTenArmedRandomRandom-v0',
            'BanditTenArmedGaussian-v0',
            'BanditTenArmedUniformDistributedReward-v0',
            'BanditTwoArmedDeterministicFixed-v0',
            'BanditTwoArmedHighHighFixed-v0',
            'BanditTwoArmedHighLowFixed-v0',
            'BanditTwoArmedLowLowFixed-v0',
        )

        ENVIRONMENTS_POEM = (
            'Haiku',
            'Tanka',
            'LineSyllableConstrainedPoem',
            'SyllableConstrainedPoem',
        )
        if 'bandits' in thought_action.content:
            name_func = 'bandits'
            l = len(ENVIRONMENTS_BANDIT)
            idx = random.randint(0, l)
            name_attribute = ENVIRONMENTS_OPTIMIZATION[idx]
        elif 'optimization' in thought_action.content:
            name_func = 'optimization'
            l = len(ENVIRONMENTS_OPTIMIZATION)
            idx = random.randint(0, l)
            name_attribute = ENVIRONMENTS_OPTIMIZATION[idx]
        elif 'poem' in thought_action.content:
            name_func = 'poem'
            l = len(ENVIRONMENTS_POEM)
            idx = random.randint(0, l)
            name_attribute = ENVIRONMENTS_POEM[idx]
        # Write a wrapper
        environment_name = 'llf-' + name_func + name_attribute + '-v0'
        env = gym.make(environment_name)
        done = False
        cumulative_reward = 0.0
        observation, info = env.reset()
        if observation['observation'] == None:
            observation['observation'] = ''

        observation['feedback'] = ''

        while not done:
            # Observation is dict having 'observation', 'instruction', 'feedback'
            # Here we print the observation and ask the user for an action

            action = input(observation['observation'] + '\n' +
                           observation['instruction'] + '\n' +
                           observation['feedback'] + '\n' +
                           'Action: ')

            # Gridworld has a text action space, so TextWrapper is not needed
            # to parse a valid action from the input string
            # pdb.set_trace()
            # action = int(action)
            observation, reward, terminated, truncated, info = env.step(action)

            if isinstance(observation['observation'], str) == False:
                observation['observation'] = ''
            if isinstance(observation['instruction'], str) == False:
                observation['instruction'] = ''
            if isinstance(observation['feedback'], str) == False:
                observation['feedback'] = ''
            # reward is never revealed to the agent; only used for evaluation

            cumulative_reward += reward

            # terminated and truncated follow the same semantics as in Gymnasium

            done = terminated or truncated

        print(f'Episode reward: {cumulative_reward}')
        # Leave the following part in test cases: extracting the conditions from the message and print.

        return observation
