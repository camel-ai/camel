from typing import Optional, List

REACT_SYSTEM_PROMPT = """
You are a helpful reasoning agent. You answer questions step by step by combining your own knowledge and external tools.

At each step, follow this format:

Question: <the question>
Thought: <your reasoning>

If you can directly answer the question, go ahead and say:
Final Answer: <your answer>

Otherwise, use a tool:
Action: <tool name from [Wikipedia, duckduckgo_search, Calculator]>
Action Input: <input for the tool>

You will then receive an Observation. Continue reasoning from there:
Observation: <tool output>
Thought: <follow-up reasoning>

Repeat Thought / Action / Observation as needed.
Once you are confident, end with:
Final Answer: <answer>
"""

class ReActAgentWrapper:
    def __init__(self, model_agent: ChatAgent, max_steps: int = 6):
        self.agent = model_agent
        self.max_steps = max_steps

    def step(self, query: str) -> ChatAgentResponse:
        history = [f"Question: {query}"]
        last_response = None
        for i in range(self.max_steps):
            prompt = "\n".join(history)
            response: ChatAgentResponse = self.agent.step(prompt)
            last_response = response
            print(f"[Step {i}] Agent Output:\n{response.msgs[-1].content}\n")

            tool_calls = response.info.get("tool_calls", [])
            if tool_calls:
                tool_result = tool_calls[0].result
                history.append(f"Observation: {tool_result}\nThought:")
                continue

            content = response.msgs[-1].content
            if "Final Answer:" in content:
                return response

            history.append("Observation: No useful tool result.\nThought:")

        return last_response

# === DEMO ===
if __name__ == "__main__":
    print("=== ReAct Agent Demo ===")
    agent = ChatAgent(system_message=REACT_SYSTEM_PROMPT)
    wrapper = ReActAgentWrapper(model_agent=agent)

    # Apple Remote test case
    question = "Aside from the Apple Remote, what other device can control the program Apple Remote was originally designed to interact with?"
    result = wrapper.step(question)
    print("\n=== Final Answer ===")
    print(result.msgs[-1].content)