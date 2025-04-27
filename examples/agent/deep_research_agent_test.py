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

# from camel.agents import ReActAgentWrapper
#
# if __name__ == "__main__":
#     agent = DeepResearchAgent()
#     query = "What are the main challenges of retrieval-augmented generation?"
#     print(agent.stepfrom typing import Optional
#
# from camel.agents import ChatAgent
# from camel.responses import ChatAgentResponse
# from camel.messages import BaseMessage
# from camel.types import OpenAIBackendRole
# from camel.toolkits.search_toolkit import SearchToolkit
# from camel.types.agents import ToolCallingRecord
#
#
# REACT_SYSTEM_PROMPT = (
#     "You are a helpful ReAct agent that can use tools to answer questions step by step. One step means a single round of conversation here.\n"
#     "At each step, you will review previous memory, remind yourself about the original question and the previous observations , and answer the original question follow this format:\n"
#     "Thought: <your reasoning>\n"
#     "If in your thought, you think you can directly answer the question, go ahead and say:\n"
#     "Final Answer: <your answer>\n"
#     "Otherwise, use the function call mechanism following your thought, and at each single step, only call one function at a time. Your output should follow the format below:\n"
#     "Action: <tool calling details>\n "
#     "Action Input: <the input to the tool>\n"
#     "Observation: <Explicitly write the output of the tool here>\n"
# )
#
# # REACT_SYSTEM_PROMPT = (
# #     "You are a helpful reasoning agent that can use tools to answer questions step by step.\n"
# #     "You should strictly follow the following format!\n"
# #     "First, think about if you can directly provide the final answer. If yes, then output your answer with the format in the following line.\n"
# #     "Thought: <your reasoning>\n"
# #     "If in your thought, you think you can answer the question correctly, then output your final answer with\n"
# #     "output your corrsponding action with the format below.\n"
# #     "Action: <your action>\n"
# #     "F"
# #     "You must follow the above React format for your output!\n"
# # )
#
# # REACT_SYSTEM_PROMPT = """
# # You are a ReAct-style agent that answers questions step by step using tools.
# #
# # At each step, follow this format:
# # Question: <the input question>
# # Thought: <your reasoning>
# # Action: <one of [Wikipedia, duckduckgo_search, Calculator]>
# # Action Input: <the input to the action>
# #
# # After you output an Action and Action Input, a tool will be automatically called.
# # You will receive an Observation in the next message like this:
# # Observation: <tool result>
# # Then continue your reasoning with:
# # Thought: <next step>
# #
# # You may repeat this Thought / Action / Action Input / Observation cycle multiple times.
# #
# # When you are ready, say:
# # Thought: I now know the final answer.
# # Final Answer: <your answer>
# #
# # You must follow this format exactly.
# # """
#
# class StopCriticAgent:
#     """
#     A lightweight utility agent that critiques whether a model's answer
#     is confident and self-contained. Used for termination checking in ReAct.
#     """
#
#     def __init__(self, chat_agent: ChatAgent):
#         self.chat_agent = chat_agent
#
#     def should_stop(self, query: str, answer: str) -> bool:
#         """
#         Ask the model if the answer is complete. Returns True if so.
#         """
#         prompt = (
#             "You are an expert judge. Below is a question and an answer."
#             "\nYour task is to decide if the answer is complete and confident."
#             "\nIf yes, respond with YES. Otherwise, respond with NO."
#             f"\n\nQuestion: {query}\n\nAnswer: {answer}\n\nJudgement:"
#         )
#         response = self.chat_agent.step(prompt)
#         content = response.msgs[-1].content.lower()
#         return "yes" in content
#
#
# class ReActAgentWrapper(ChatAgent):
#     """
#     A wrapper around ChatAgent that supports ReAct-style multi-step reasoning
#     using tools, optionally enhanced with a termination critic.
#
#     Attributes:
#         stop_critic (StopCriticAgent): Optional critic for determining termination.
#     """
#
#     def __init__(
#         self,
#         *args,
#         stop_critic: Optional[StopCriticAgent] = None,
#         max_steps: int = 5,
#         system_message: Optional[str] = None,
#         **kwargs,
#     ) -> None:
#         if system_message is None:
#             system_message = REACT_SYSTEM_PROMPT
#
#         super().__init__(system_message=system_message, *args, **kwargs)
#         self.max_steps = max_steps
#         self.stop_critic = stop_critic
#         self._obs_prefix = "\nObservation:"
#         self._thought_prefix = "\nThought:"
#
#     def reset(self, *args, **kwargs) -> None:
#         super().reset(*args, **kwargs)
#
#     def step(self, query: str) -> ChatAgentResponse:
#         """
#         Performs ReAct reasoning until no tool is called or critic allows termination.
#         """
#         msg = query
#         last_response: Optional[ChatAgentResponse] = None
#
#         for _ in range(self.max_steps):
#             response = super().step(msg)
#             last_response = response
#             print("Check Response", last_response)
#             tool_calls: list[ToolCallingRecord] = response.info.get("tool_calls", [])
#
#             if tool_calls:
#                 print("Check tool calls", tool_calls)
#                 result = tool_calls[-1].result
#                 msg = f"{self._obs_prefix} {result}{self._thought_prefix}"
#                 print("Check tool call mesage", msg)
#                 continue
#
#             final_answer = response.msgs[-1].content
#             if self.stop_critic is None or self.stop_critic.should_stop(query, final_answer):
#                 response.msgs[-1].content = self._extract_final_answer(final_answer)
#                 return response
#             else:
#                 msg = f"{self._obs_prefix} The previous answer may be incomplete.\nThought:"
#
#         if last_response is not None:
#             last_response.msgs[-1].content = self._extract_final_answer(last_response.msgs[-1].content)
#             return last_response
#         return super().step("Final Answer:")
#
#     def _extract_final_answer(self, content: str) -> str:
#         """
#         Parse the model's final output and extract only the Final Answer, if available.
#         """
#         #if "Final Answer:" in content:
#         #    return content.split("Final Answer:")[-1].strip()
#         return content.strip()
#
#
# def print_trace(agent, title="Prompt Trace"):
#     """
#     Print the current prompt content from an agent's memory.
#     Supports any ChatAgent or ReActAgentWrapper instance.
#     """
#     print(f"\n======= {title} =======")
#     try:
#         messages, _ = agent.memory.get_context()
#     except Exception as e:
#         print("Failed to get context from agent memory:", e)
#         return
#
#     for m in messages:
#         print("Current Message in memory: \n")
#         role = m.get("role", "").upper()
#         content = m.get("content", "").strip()
#         print(f"{role}: {content}\n")
#     print(f"======= End of Trace =======\n")
#
#
# if __name__ == "__main__":
#     from camel.toolkits import FunctionTool
#     def add(a: int, b: int) -> int:
#         r"""Adds two numbers.
#
#         Args:
#             a (int): The first number to be added.
#             b (int): The second number to be added.
#
#         Returns:
#             integer: The sum of the two numbers.
#         """
#         return a + b
#
#
#     # Wrap the function with FunctionTool
#     add_tool = FunctionTool(add)
#
#     # Initialize the base chat agent with a tool
#     base_agent = ChatAgent(
#         system_message="You are a helpful assistant using tools.",
#         tools=[SearchToolkit().search_duckduckgo],
#     )
#
#     base_agent1 = ChatAgent(
#         system_message="You are a helpful assistant using tools.",
#     )
#
#     # Build ReAct agent with optional termination critic
#     react_agent = ReActAgentWrapper(
#         tools=base_agent.tool_dict.values(),
#         stop_critic=StopCriticAgent(base_agent),
#     )
#
#     questions = [
#         #"I have 3 apples, my wife gives me two more, and my brother give me one more, and I give one to my sister, how many apples do I have?",
#         "Aside from the Apple Remote, what other device can control the program Apple Remote was originally designed to interact with?",
#         #"What is the GDP per capita of India compared to Brazil in 2022?",
#         #"List the CEO names of OpenAI, Anthropic, and Google DeepMind in 2024.",
#         #"Compare the emissions of China and the US in 2022.",
#     ]
#
#     for query in questions:
#         print("\n=== Question ===")
#         print(query)
#
#         print("\n[ReActAgentWrapper Response]")
#         react_response = react_agent.step(query)
#         print("Answer:\n", react_response.msgs[-1].content)
#
#         print_trace(react_agent, title="Prompt Trace")
#
#         print("\n[Baseline ChatAgent Response]")
#         base_response = base_agent1.step(query)
#         print("Answer:", base_response.msgs[-1].content)
#
#         print("\n------------------------------")(query))


from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.toolkits import (
    SearchToolkit,
    # MathToolkit,
    # GoogleMapsToolkit,
    # TwitterToolkit,
    # WeatherToolkit,
    # RetrievalToolkit,
    # TwitterToolkit,
    # SlackToolkit,
    # LinkedInToolkit,
    # RedditToolkit,
)
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from typing import Optional, List
from camel.toolkits import FunctionTool
tools_list = [
    # *MathToolkit().get_tools(),
    *SearchToolkit().get_tools(),
]
model=ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI
)

def format_allowed_tool_names(tools: List[FunctionTool]) -> str:
    tool_names = [tool.get_function_name() for tool in tools]
    joined = "\n".join(f"- {name}" for name in tool_names)
    return (
        "The following is the list of tools the worker agent is allowed to use. "
        "Tool names are case-sensitive and must match exactly. "
        "You must only use tools from this list.\n\n"
        f"Allowed Tools:\n{joined}"
    )

def describe_tools_naturally_en(tools: List[FunctionTool]) -> str:
    lines = [""]
    for tool in tools:
        schema = tool.get_openai_function_schema()
        name = schema.get("name", "")
        desc = schema.get("description", "").strip()
        params = schema.get("parameters", {}).get("properties", {})
        param_strs = []
        for pname, pinfo in params.items():
            pdesc = pinfo.get("description", "").strip()
            param_strs.append(f"  - Parameter `{pname}`: {pdesc}")
        param_section = "\n".join(param_strs) if param_strs else "  - This tool has no parameters."
        lines.append(f"\n* Tool Name: `{name}`\n  Description: {desc}\n{param_section}")
    return "\n".join(lines)
def get_tool_constraint_instruction(tools: List[FunctionTool]) -> str:
    tool_names = [tool.get_function_name() for tool in tools]
    formatted = ", ".join(tool_names)
    return (
        "You MUST only use tools listed in the <AllowedTools> section. "
        "Tool names are case-sensitive and must match exactly.\n"
        "Do NOT invent tool names such as 'Search', 'SearchOnline', etc.\n"
        f"Valid tools include: {formatted}\n"
    )
def build_tool_prompt_section(tools: List[FunctionTool]) -> str:
    return (
        format_allowed_tool_names(tools) + "\n\n" +
        "Tool Descriptions:\n" +
        describe_tools_naturally_en(tools)
    )

def build_tool_prompt_section_complete(tools: List[FunctionTool]) -> str:
    tool_names = [tool.get_function_name() for tool in tools]
    tool_list_str = "\n".join(f"- {name}" for name in tool_names)

    # Tool Descriptions
    desc_lines = []
    for tool in tools:
        schema = tool.get_openai_function_schema()
        name = schema.get("name", "")
        desc = schema.get("description", "").strip()
        params = schema.get("parameters", {}).get("properties", {})
        param_lines = [
            f"  - Parameter `{pname}`: {pinfo.get('description', '').strip()}"
            for pname, pinfo in params.items()
        ]
        param_block = "\n".join(param_lines) if param_lines else "  - No parameters"
        desc_lines.append(f"* Tool Name: `{name}`\n  Description: {desc}\n{param_block}")
    tool_desc_str = "\n\n".join(desc_lines)

    # Return prompt section
    return (
        get_tool_constraint_instruction(tools) + "\n" +
        "<AllowedTools>\n" + tool_list_str + "\n</AllowedTools>\n\n" +
        "<ToolDescriptions>\n" + tool_desc_str + "\n</ToolDescriptions>"
    )

def format_planner_prompt(query: str, tools_list = [], previous_plan: Optional[str] = None, previous_observations: Optional[str] = None) -> str:
    # --- System preamble ---
    prompt = (
        "You are the planner agent of the Camel-AI Deep Research Agent for solving complex and difficult problems. "
        "You will be given a Query, which can be a task or a question. You are supposed to give a detailed plan of resolving the query. The worker agents will then work on the plan. You can assume the worker agents can call tools like Search Online, and Do Calculation. You will later have chance to make more plans based on the information gathered by worker agents.\n"
        "You do not need to select tools or know implementation details. Just describe the **intent** of each step clearly."
        "Never forget the Query. \n"
    )
    prompt += f"Query: {query}\n"

    # --- Replanning instruction if applicable ---
    if (previous_plan and previous_observations):
        prompt += (
            "You are now in a re-planning stage. You are provided additional Previous Plan and Previous Observations of solving the same Query and be asked to do more planning. "
            "Please do not change the previous plan and just attach new plans to the current plan.\n"
        )

        # --- Query and context ---

        prompt += f"\nPrevious Plan:\n{previous_plan}\n"
        prompt += f"\nPrevious Observations:\n{previous_observations}\n"
        prompt += (f"\nPlease Think about query, with the previous plan and observations.\n"
                   "\n If the previous observations has already resolved the origin query, please just output your Thought as the line below:\n"
                   "$Thought$: $resolved$\n"
                   "\n Other wise, please generate an additional plan that are following steps of the original plan. "
                   "When making the new plan, please first repeat the original plan with exactly the same words and format line by line, and then generate additional plan below it."
                    "Write your output in the format of\n"
                   "\n$Thought$:\n<Thought about the query>\n"
                   "\n$Plan$:\n<Attach the Previous plan exactly, and attach an additional step-by-step plan to resolve the original query, to the current plan>\n"
                    "\nThe plan should be a set of actionable sub-queries, each one take a line. The sub-queries have an order, but please do not explicitly output the order. Just return the pure queries. Each sub-query takes a single line.\n"
                    "\nNow, begin your think and plan process.\n"
                    "\n$Thought$:\n"
                )
    # --- Final plan start ---
    # prompt += ("\nPlease Think about the query and return the plan below. Write your output in the format of\n"
    #            "\n$Thought$:\n<Thought about the query>\n"
    #            "\n$Plan$:\n<A step-by-step plan to resolve the original query>\n"
    #            "\nThe plan should be a set of actionable sub-queries, each one take a line. The sub-queries have an order, but please Do Not Explicitly Output the order! Just return the Pure sub-queries without order number. Each sub-query takes a single line.\n"
    #            "During the plan-making process, if you find you need more tool call, you MUST STOP the plan making, and just output the tools to be called, and the input for the tools, then stop your output by saying 'I can continue to make the plan after I gather the necessary observations.'\n"
    #            #"\n You are equipped with tool calling ability. If you feel you need more observations, you can choose not to make the plan, but do function call instead. The user will later continue the conversation with you, to continue the plan making process."
    #            #"\nNow, begin your think and plan process.\n"
    #            #"\n$Thought$:\n"
    #            )

    # prompt += (
    #     "\nNow begin your reasoning and planning. Follow one of the two branches below:\n"
    #     "\nIf you have sufficient knowledge to complete the plan, write:\n"
    #     "$Thought$:\n<Your reasoning>\n"
    #     "$Plan$:\n<Each sub-task in a single line>\n"
    #     "\nThe plan should be a list of concrete sub-queries, each written on its own line. Do not add numbering or ordering prefixes.\n"
    #     "\nIf you do NOT have sufficient information to make a complete plan and find tool calling (for example, searching online) is necessary:\n"
    #     "  - DO NOT write $Plan$.\n"
    #     "  - Instead, write:\n"
    #     "\n$Thought$:\n<Explain what information is missing>\n"
    #     "\n$ToolCalls$:\n- Tool: <tool name from AllowedTools section >\n  Input: <input for the tool>\n"
    #     "\nThen say: 'I can continue to make the plan after I gather the necessary observations.'\n"
    #
    # )

    prompt += (
        "\nNow begin your reasoning and planning. Follow one of the two branches below:\n"
        "\nIf you have sufficient knowledge to complete the plan, write:\n"
        "$Thought$:\n<Your reasoning>\n"
        "$Plan$:\n<Each sub-task in a single line>\n"
        "\nThe plan should be a list of concrete sub-queries, each written on its own line. Do not add numbering or ordering prefixes.\n"
        "\nIf you do NOT have sufficient information to make a complete plan then you should gather more observations. If the query involves an entity that cannot be directly resolved (e.g., a person, TV show, event, or technical term),"
        " you MUST first identify or disambiguate the entity before continuing the plan."
        "For example, if the query contains a phrase like a lyric or a vague name, your first step should be to identify what it refers to.\n"
        "Follow the instructions below:\n"
        "- First, identify what is missing (e.g. the identity of a key subject, or data required to reason further).\n"
        "- Then, generate a set of tool calls that can help fill in the missing knowledge.\n"
        "- Each tool call should correspond to a specific sub-query and clearly indicate intent.\n"
        "\n$Thought$:\n<Explain what information is missing>\n"
        "$Plan$:\n"
        "Use toolkit to solve the problem. $Tool$: <general name, e.g. Search Online, Calculation>. $Input$: <input for the tool>\n"
        "Use toolkit to solve the problem. $Tool$: <general name, e.g. Search Online, Calculation>. $Input$: <input for the tool>\n"
        "... (you may include multiple tool calls if helpful)\n"
    )


    return prompt



#print(describe_tools_naturally_en(tools_list ))
query = "我二十年前看了一个儿童节目，主题曲里有一句是“咕噜咕噜咕噜咕咚咚”，我想请你帮我介绍一下这个节目的主持人，和他们的现状。"
#query = "Help me draft a report for the Camel-AI open source project"
#query = "请你回答这个以几个中国春晚著名节目为背景的搞笑问题：买一杯宫廷玉液酒，再请黄大锤使用大锤和小锤一起掏壁橱，一共花多少钱。"
print(format_planner_prompt(query,tools_list))

# Set the agent
agent = ChatAgent(
    format_planner_prompt(query),
    model=model,
    #tools=tools_list,
    output_language = "Chinese",
)



response = agent.step("Now let us begin.")
content = response.msgs[0].content  # 就是你需要的字符串输出
print(content)

import re

def extract_plan_subqueries(content: str) -> list[str]:
    # 匹配 $Plan$ 后的部分
    match = re.search(r"\$Plan\$:([\s\S]+)", content)
    if not match:
        return []

    plan_block = match.group(1).strip()
    lines = [line.strip() for line in plan_block.split("\n") if line.strip()]
    return lines


subqueries = extract_plan_subqueries(content)
print(subqueries)


worker_agent_prompt = ("You are a helpful worker agent in the Camel-AI Deep Research Agent system. Your goal is to solve tasks that the planner assigned to you."
                       "Your have tool calling ability. Please try your best to give the answer with tool calling. If you really cannot find the answer even"
                       "with the help of the tool, then just return 'I do not know'. Please do not make up answers, as it will influence the result!")

# Set the agent
worker_agent = ChatAgent(
    worker_agent_prompt ,
    model=model,
    tools=tools_list,
    output_language = "Chinese",
)

subquery_history = {}
for subquery in subqueries:
    print(f"Now using worker agent to answer the subquery {subquery}")

    worker_agent.reset()  # Todo: Double check the usage of reset.
    subquery_response = worker_agent.step(subquery)
    print("Answer for this subquery:", subquery_response.msgs[0].content)
    subquery_history[subquery] = subquery_response.msgs[0].content

print(subquery_history)