# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
from typing import Callable

from camel.agents import ChatAgent


class LLMScoreEvaluator:
    """LLM based evaluator."""

    def __init__(
        self,
        agent: ChatAgent,
        prompt_builder: Callable[..., str],
        default_score: float = 0.0,
    ):
        """
        Args:
            agent: ChatAgent instance
            prompt_builder: function that returns a prompt string
            default_score: fallback score on failure
        """
        self.agent = agent
        self.prompt_builder = prompt_builder
        self.default_score = default_score

    def evaluate(self, **kwargs) -> float:
        try:
            prompt = self.prompt_builder(**kwargs)
            response = self.agent.step(prompt)
            score = response.msg.content.strip()
            return float(score)

        except Exception:
            return self.default_score


def build_context_relevance_prompt(question: str, contexts: list[str]) -> str:
    context_text = "\n\n".join(
        f"Context {i+1}: {c}" for i, c in enumerate(contexts)
    )

    return f"""You are an expert evaluator. Given a question and retrieved contexts,
rate how relevant the contexts are to answering the question.

Question: {question}

Contexts:
{context_text}

Provide a single relevance score from 0.0 to 1.0, where:
- 0.0: Contexts are completely irrelevant
- 0.5: Contexts are somewhat relevant
- 1.0: Contexts are highly relevant and sufficient to answer the question

Respond with only the numeric score, nothing else."""


def build_faithfulness_prompt(
    question: str,
    contexts: list[str],
    answer: str,
) -> str:
    context_text = "\n\n".join(
        f"Context {i+1}: {c}" for i, c in enumerate(contexts)
    )

    return f"""You are an expert evaluator. Given a question, retrieved contexts,
and a generated answer, rate how faithful the answer is to the contexts.

Question: {question}

Contexts:
{context_text}

Generated Answer: {answer}

Provide a faithfulness score from 0.0 to 1.0, where:
- 0.0: Answer is completely unfaithful
- 0.5: Answer is somewhat faithful
- 1.0: Answer is fully faithful

Respond with only the numeric score, nothing else."""
