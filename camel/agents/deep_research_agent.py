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


class DeepResearchAgent(BaseAgent):
    r"""A minimal research agent that performs query-based document retrieval and summarization.

    This agent fetches live Wikipedia content based on the query and summarizes it into a markdown answer.
    """

    def __init__(
        self,
        top_k: int = 3,
        retriever: Optional[AutoRetriever] = None,
        summarizer: Optional[SearchAgent] = None,
    ) -> None:
        # Default retriever: wraps SearchToolkit with search_wiki()
        self.retriever = retriever or AutoRetriever(tool=SearchToolkit())
        self.summarizer = summarizer or SearchAgent()
        self.top_k = top_k

    def reset(self, *args: Any, **kwargs: Any) -> None:
        if hasattr(self.retriever, "reset"):
            self.retriever.reset()
        if hasattr(self.summarizer, "reset"):
            self.summarizer.reset()

    def step(self, query: str) -> str:
        """Run a research step: retrieve → summarize → format."""
        documents = self.retriever.retrieve(query, top_k=self.top_k)
        if not documents:
            return f"**No relevant documents found for:** {query}"

        # Join content for summarizer
        full_text = "\n\n".join([doc["content"] for doc in documents])
        summary = self.summarizer.summarize_text(full_text, query)

        output = f"## Query\n{query}\n\n"
        output += f"## Answer\n{summary.strip()}\n\n"
        output += "## Sources\n"
        for doc in documents:
            title = doc.get("source", "Wikipedia")
            url = doc.get("url", None)
            output += f"- [{title}]({url})\n" if url else f"- {title}\n"

        return output


from typing import Optional

from camel.agents import ChatAgent
from camel.responses import ChatAgentResponse
from camel.messages import BaseMessage
from camel.types import OpenAIBackendRole

REACT_SYSTEM_PROMPT = (
    "You are a helpful agent that uses tools to answer complex questions step by step.\n"
    "Follow the format:\n"
    "Thought: <your reasoning>\n"
    "Action: <tool name>\n"
    "Action Input: <tool input>\n"
    "Observation: <tool result>\n"
    "Thought: <your updated reasoning>\n"
    "Final Answer: <your answer if ready>\n"
)


class StopCriticAgent:
    r"""
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
            "\nIf yes, respond with YES. Otherwise, respond with NO."
            f"\n\nQuestion: {query}\n\nAnswer: {answer}\n\nJudgement:"
        )
        response = self.chat_agent.step(prompt)
        content = response.msgs[-1].content.lower()
        return "yes" in content


class ReActAgentWrapper(ChatAgent):
    r"""
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
            tool_calls = response.info.get("tool_calls", [])

            if tool_calls:
                result = tool_calls[-1]["result"]
                msg = f"{self._obs_prefix} {result}{self._thought_prefix}"
                continue

            # No tool call, check with stop critic if provided
            final_answer = response.msgs[-1].content
            if self.stop_critic is None or self.stop_critic.should_stop(query, final_answer):
                return response
            else:
                msg = f"{self._obs_prefix} The previous answer may be incomplete.\nThought:"

        # Reached max steps without termination, return last response anyway
        return last_response or super().step("Final Answer:")


# # ==== Example Usage ====
# if __name__ == "__main__":
#     from camel.toolkits.search_toolkit import SearchToolkit
#
#     chat_agent = ChatAgent(
#         system_message="You are a helpful agent. Think step by step and use tools if needed.",
#         tools=[SearchToolkit().search_duckduckgo],
#     )
#     stop_critic = StopCriticAgent(chat_agent)
#     react_agent = ReActAgentWrapper(
#         tools=chat_agent.tool_dict.values(),
#         stop_critic=stop_critic,
#     )
#
#     query = "Who is the president of France and what is his latest speech about?"
#     response = react_agent.step(query)
#     print("Final Answer:\n", response.msgs[-1].content)
