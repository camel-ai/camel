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


from typing import Optional

from camel.agents import ChatAgent
from camel.responses import ChatAgentResponse
from camel.messages import BaseMessage
from camel.types import OpenAIBackendRole
from camel.toolkits.search_toolkit import SearchToolkit
from camel.types.agents import ToolCallingRecord


REACT_SYSTEM_PROMPT = (
    "You are a helpful ReAct agent that can use tools to answer questions step by step. One step means a single round of conversation here.\n"
    "At each step, you will review previous memory, remind yourself about the original question and the previous observations , and answer the original question follow this format:\n"
    "Thought: <your reasoning>\n"
    "If in your thought, you think you can directly answer the question, go ahead and say:\n"
    "Final Answer: <your answer>\n"
    "Otherwise, use the function call mechanism following your thought, and at each single step, only call one function at a time. Your output should follow the format below:\n"
    "Action: <tool calling details>\n "
    "Action Input: <the input to the tool>\n"
    "Observation: <Explicitly write the output of the tool here>\n"
)

# REACT_SYSTEM_PROMPT = (
#     "You are a helpful reasoning agent that can use tools to answer questions step by step.\n"
#     "You should strictly follow the following format!\n"
#     "First, think about if you can directly provide the final answer. If yes, then output your answer with the format in the following line.\n"
#     "Thought: <your reasoning>\n"
#     "If in your thought, you think you can answer the question correctly, then output your final answer with\n"
#     "output your corrsponding action with the format below.\n"
#     "Action: <your action>\n"
#     "F"
#     "You must follow the above React format for your output!\n"
# )

# REACT_SYSTEM_PROMPT = """
# You are a ReAct-style agent that answers questions step by step using tools.
#
# At each step, follow this format:
# Question: <the input question>
# Thought: <your reasoning>
# Action: <one of [Wikipedia, duckduckgo_search, Calculator]>
# Action Input: <the input to the action>
#
# After you output an Action and Action Input, a tool will be automatically called.
# You will receive an Observation in the next message like this:
# Observation: <tool result>
# Then continue your reasoning with:
# Thought: <next step>
#
# You may repeat this Thought / Action / Action Input / Observation cycle multiple times.
#
# When you are ready, say:
# Thought: I now know the final answer.
# Final Answer: <your answer>
#
# You must follow this format exactly.
# """

class StopCriticAgent:
    """
    A lightweight utility agent that critiques whether a model's answer
    is confident and self-contained. Used for termination checking in ReAct.
    """

    def __init__(self, chat_agent: ChatAgent):
        self.chat_agent = chat_agent

    def should_stop(self, query: str, answer: str) -> bool:
        """
        Ask the model if the answer is complete. Returns True if so.
        """
        prompt = (
            "You are an expert judge. Below is a question and an answer."
            "\nYour task is to decide if the answer is complete and confident."
            "\nIf yes, respond with YES. Otherwise, respond with NO, and explain the reason. Tell me "
            f"\n\nQuestion: {query}\n\nAnswer: {answer}\n\nJudgement:"
        )
        response = self.chat_agent.step(prompt)
        content = response.msgs[-1].content.lower()

        print(Content)
        return "yes" in content


class ReActAgentWrapper(ChatAgent):
    """
    A wrapper around ChatAgent that supports ReAct-style multi-step reasoning
    using tools, optionally enhanced with a termination critic.

    Attributes:
        stop_critic (StopCriticAgent): Optional critic for determining termination.
    """

    def __init__(
        self,
        *args,
        stop_critic: Optional[StopCriticAgent] = None,
        max_steps: int = 5,
        system_message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if system_message is None:
            system_message = REACT_SYSTEM_PROMPT

        super().__init__(system_message=system_message, *args, **kwargs)
        self.max_steps = max_steps
        self.stop_critic = stop_critic
        self._obs_prefix = "\nObservation:"
        self._thought_prefix = "\nThought:"

    def reset(self, *args, **kwargs) -> None:
        super().reset(*args, **kwargs)

    def step(self, query: str) -> ChatAgentResponse:
        """
        Performs ReAct reasoning until no tool is called or critic allows termination.
        """
        msg = query
        last_response: Optional[ChatAgentResponse] = None

        for _ in range(self.max_steps):
            response = super().step(msg)
            last_response = response
            print("Check Response", last_response)
            tool_calls: list[ToolCallingRecord] = response.info.get("tool_calls", [])

            if tool_calls:
                print("Check tool calls", tool_calls)
                result = tool_calls[-1].result
                msg = f"{self._obs_prefix} {result}{self._thought_prefix}"
                print("Check tool call message", msg)
                continue

            final_answer = response.msgs[-1].content
            if self.stop_critic is None or self.stop_critic.should_stop(query, final_answer):
                response.msgs[-1].content = self._extract_final_answer(final_answer)
                return response
            else:
                msg = f"{self._obs_prefix} The previous answer may be incomplete.\nThought:"

        if last_response is not None:
            last_response.msgs[-1].content = self._extract_final_answer(last_response.msgs[-1].content)
            return last_response
        return super().step("Final Answer:")

    def _extract_final_answer(self, content: str) -> str:
        """
        Parse the model's final output and extract only the Final Answer, if available.
        """
        #if "Final Answer:" in content:
        #    return content.split("Final Answer:")[-1].strip()
        return content.strip()


def print_trace(agent, title="Prompt Trace"):
    """
    Print the current prompt content from an agent's memory.
    Supports any ChatAgent or ReActAgentWrapper instance.
    """
    print(f"\n======= {title} =======")
    try:
        messages, _ = agent.memory.get_context()
    except Exception as e:
        print("Failed to get context from agent memory:", e)
        return

    for m in messages:
        print("Current Message in memory: \n")
        role = m.get("role", "").upper()
        content = m.get("content", "").strip()
        print(f"{role}: {content}\n")
    print(f"======= End of Trace =======\n")


if __name__ == "__main__":
    from camel.toolkits import FunctionTool
    def add(a: int, b: int) -> int:
        r"""Adds two numbers.

        Args:
            a (int): The first number to be added.
            b (int): The second number to be added.

        Returns:
            integer: The sum of the two numbers.
        """
        return a + b


    # Wrap the function with FunctionTool
    add_tool = FunctionTool(add)

    # Initialize the base chat agent with a tool
    base_agent = ChatAgent(
        system_message="You are a helpful assistant using tools.",
        tools=[SearchToolkit().search_duckduckgo],
    )

    base_agent1 = ChatAgent(
        system_message="You are a helpful assistant using tools.",
    )

    # Build ReAct agent with optional termination critic
    react_agent = ReActAgentWrapper(
        tools=base_agent.tool_dict.values(),
        stop_critic=StopCriticAgent(base_agent),
    )

    questions = [
        #"I have 3 apples, my wife gives me two more, and my brother give me one more, and I give one to my sister, how many apples do I have?",
        "Aside from the Apple Remote, what other device can control the program Apple Remote was originally designed to interact with?",
        #"What is the GDP per capita of India compared to Brazil in 2022?",
        #"List the CEO names of OpenAI, Anthropic, and Google DeepMind in 2024.",
        #"Compare the emissions of China and the US in 2022.",
    ]

    for query in questions:
        print("\n=== Question ===")
        print(query)

        print("\n[ReActAgentWrapper Response]")
        react_response = react_agent.step(query)
        print("Answer:\n", react_response.msgs[-1].content)

        print_trace(react_agent, title="Prompt Trace")

        print("\n[Baseline ChatAgent Response]")
        base_response = base_agent1.step(query)
        print("Answer:", base_response.msgs[-1].content)

        print("\n------------------------------")