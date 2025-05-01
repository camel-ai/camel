# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

from typing import Any, Optional

from camel.agents.base import BaseAgent
from camel.agents.search_agent import SearchAgent
from camel.retrievers.auto_retriever import AutoRetriever
from camel.toolkits.search_toolkit import SearchToolkit
from camel.agents.chat_agent import ChatAgent

# AgentOps decorator setting
try:
    import os

    if os.getenv("AGENTOPS_API_KEY") is not None:
        from agentops import track_agent
    else:
        raise ImportError
except (ImportError, AttributeError):
    from camel.utils import track_agent

@track_agent(name="DeepResearchAgent")
class DeepResearchAgent(BaseAgent):
    def __init__(
            self,
            query: str,
            tools: List[FunctionTool],
            model: Optional[Union[BaseModelBackend, List[BaseModelBackend]],
        ] = None,
    ) -> None:
        self.query = query
        self.tools = tools
        self.model = model
        # Todo: Think about how memory for worker/writer
        #  can be better customized

    @staticmethod
    def format_planner_prompt(query: str) -> str:
        # --- System preamble ---
        prompt = (
            "You are the planner agent of the Camel-AI Deep Research Agent for solving complex and difficult problems. "
            "You will be given a Query, which can be a task or a question. You are supposed to give a detailed plan of resolving the query. The worker agents will then work on the plan. You can assume the worker agents can call tools like Search Online, and Do Calculation. You will later have chance to make more plans based on the information gathered by worker agents.\n"
            "You do not need to select tools or know implementation details. Just describe the **intent** of each step clearly."
            "Never forget the Query. \n"
        )
        prompt += f"Query: {query}\n"

        prompt += (
            "\nNow begin your reasoning and planning. Follow one of the two branches below:\n"
            "\nIf you have sufficient knowledge to complete the plan, write:\n"
            "$Thought$:\n<Your reasoning>\n"
            "$Plan$:\n<Each sub-task in a single line>\n"
            "\nThe plan should be a list of concrete sub-queries, each written on its own line. Do not add numbering or ordering prefixes.\n\n"
            "\nIf you do NOT have sufficient information to make a complete plan then you should gather more observations ONE AT A TIME. If the query involves an entity that cannot be directly resolved (e.g., a person, TV show, event, or technical term),"
            " you MUST first identify or disambiguate the entity before continuing the plan."
            "For example, if the query contains a phrase like a lyric or a vague name, your first step should be to identify what it refers to.\n"
            "Follow the instructions below:\n"
            "- First, identify what is missing (e.g. the identity of a key subject, or data required to reason further).\n"
            "- Then, generate ONE MOST important NEXT tool call that can help fill in the missing knowledge IN A SINGLE LINE.\n"
            "You can Follow the example format below:\n"
            #"- Each tool call should correspond to a specific sub-query and clearly indicate intent.\n"
            "\n$Thought$:\n<Explain what information is missing>\n"
            "$Plan$:\n"
            "Use toolkit to solve the problem. $Tool$: <general name, e.g. Search Online, Calculation>. $Input$: <input for the tool>\n"
        )



    @staticmethod
    def format_replanner_prompt(query: str, plan_obs_dict: dict) -> str:
        prompt = (
            "You are the planner agent of the Camel-AI Deep Research Agent for solving complex and difficult problems. "
            "You are given a Query and the previous planning history, including prior sub-queries (plans) and corresponding observations. "
            "Your goal is to continue the planning process based on the original Query and the Observations from previous plans.  The worker agents will then work on the plan. You can assume the worker agents can call tools to Search Online. You will later have chance to make more plans based on the information gathered by worker agents. "
            "You must consider the previous plans and their corresponding observations. You are NOT allowed to modify existing plans, "
            "but you may append new steps as actionable subqueries if the original Query is not yet fully resolved.\n\n"
            f"Query:\n{query}\n\n"
            "Previous Plan and Observation Pairs:\n"
        )

        for plan, obs in plan_obs_dict.items():
            prompt += f"<Plan>\n{plan.strip()}\n</Plan>\n<Observation>\n{obs.strip()}\n</Observation>\n\n"

        prompt += (
            "Now, begin your reasoning and planning. Follow one of the two branches below:\n\n"
            "If you **truly** believe the query has been fully resolved:\n"
            "-Only choose this branch **if and only if**:\n"
            "1. The retrieved information clearly covers **all aspects** of the original query;\n"
            "2. You have verified that no further clarification, comparison, or synthesis is necessary;\n"
            "3. There is enough information for the writer agent to compose a complete and structured answer;\n"
            "4. You have seen a clear and complete plan in previous results.\n"
            "- Otherwise, **do not stop the planning process**.\n\n"
            "$Thought$:\n<Your reasoning>\n"
            # "$Answer$:\n<Your answer to the original query>\n"
            "$Problem_Resolved$\n\n"
    
    
            "If the query is not fully resolved:\n"
            "$Thought$:\n<Your reasoning>\n"
            "$Plan$:\n"
            "Add new plans as step by step sub-queries to resolve the remaining parts of the original query. Each sub-query should be a single line"
            "Do not add numbering or ordering prefixes.\n\n"
            "\nIf you do NOT have sufficient information to make a complete plan then you should gather more observations ONE AT A TIME. If the query involves an entity that cannot be directly resolved (e.g., a person, TV show, event, or technical term),"
            " you MUST first identify or disambiguate the entity before continuing the plan."
            "For example, if the query contains a phrase like a lyric or a vague name, your first step should be to identify what it refers to.\n"
            "Follow the instruction below if you need more information:\n"
            "Instead of adding direct sub-queries, list ONE MOST important next tool-based query that the worker agents should perform to gather the missing information IN A SINGLE LINE.\n"
            "$Thought$:\n<Explain what information is missing>\n"
            "$Plan$:\n"
            "Use toolkit to solve the problem. $Tool$: Search Online. $Input$: <input for the tool>\n"
        )

        return prompt

    @staticmethod
    def format_summarizer_prompt(query,plan_obs_dict):
        summarizer_agent_prompt = (
            "You are the writer agent in the CAMEL-AI Deep Research Agent system. "
            "Your task is to synthesize a final report to the original query using all prior plan-observation pairs.\n\n"
            "You should:\n"
            "- Carefully review all prior plans and their corresponding observations.\n"
            "- Revise or refine the original plan.\n"
            "- Identify relevant, accurate, and insightful information from observations.\n"
            "- Compose a coherent and complete final report.\n\n"
            "Please keep the original query clearly in mind throughout the writing process.\n\n"
            f"Original Query:\n{query}\n\n"
            "Plan and Observation History:\n"
        )
        for plan, obs in plan_obs_dict.items():
            summarizer_agent_prompt += (
                f"<Plan>\n{plan.strip()}\n</Plan>\n"
                f"<Observation>\n{obs.strip()}\n</Observation>\n\n"
            )


    def step(self, query, output_language, max_planning_iterations = 10):
        r"""docstring"""
        # Set the planner agent
        planner_agent = ChatAgent(
            DeepResearchAgent.format_planner_prompt(query),
            model=self.model,
            # tools=tools_list,
            output_language= output_language,
        )

        response = planner_agent.step("Now begin planning.")
        content = response.msgs[0].content
        logger.info(print(content))


    def reset(self):
        r"The deep research agent does not have state, so do not need reset"
        pass

