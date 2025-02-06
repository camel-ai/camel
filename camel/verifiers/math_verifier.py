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


import re
from typing import Any, ClassVar, Dict, Optional

from datasets import Dataset

from camel.agents import ChatAgent
from camel.responses import ChatAgentResponse
from camel.verifiers.base_verifier import BaseVerifier
from camel.verifiers.types import VerificationResult


class MathVerifier(BaseVerifier):
    """Verifier for mathematical problems using LLM."""

    DEFAULT_CRITERIA: ClassVar[Dict[str, Any]] = {
        "numerical_tolerance": 1e-6,
        "verify_steps": True,
    }

    def __init__(
        self,
        criteria: Optional[Dict[str, Any]] = None,
        agent: Optional[ChatAgent] = None,
    ) -> None:
        """Initialize the verifier.

        Args:
            criteria: Optional verification criteria
            agent: ChatAgent instance for verification
        """
        super().__init__(criteria)
        self.agent = agent

    def verify(
        self, data: Dataset, criteria: Optional[Dict[str, Any]] = None
    ) -> Dataset:
        """Verify mathematical solutions in the dataset."""
        criteria = {**self.DEFAULT_CRITERIA, **(criteria or {})}

        def verify_single(example):
            result = self._verify_solution(
                question=example["question"],
                solution=example["solution"],
                answer=example.get("answer"),
                criteria=criteria,
            )

            example["verification_result"] = result.dict()
            example["correct"] = result.passed
            return example

        return data.map(verify_single)

    def _verify_solution(
        self,
        question: str,
        solution: str,
        answer: Optional[str] = None,
        criteria: Optional[Dict[str, Any]] = None,
    ) -> VerificationResult:
        """Verify a single mathematical solution using LLM."""
        try:
            # Extract boxed answers
            solution_value = self._extract_boxed_answer(solution)
            answer_value = (
                self._extract_boxed_answer(answer) if answer else None
            )

            if not solution_value:
                return VerificationResult(
                    score=0.0,
                    passed=False,
                    details={"error": "No \\boxed{} answer found"},
                    feedback="Solution must include a \\boxed{} answer",
                    error=None,
                )

            # Construct prompt for LLM
            prompt = self._construct_verification_prompt(
                question=question, solution=solution_value, answer=answer_value
            )

            if self.agent is None:
                raise ValueError("ChatAgent not initialized")

            # Get LLM response
            response: ChatAgentResponse = self.agent.step(prompt)
            verification_result = self._parse_llm_response(
                response.msgs[0].content
            )

            return VerificationResult(
                score=verification_result["score"],
                passed=verification_result["passed"],
                details=verification_result["details"],
                feedback=verification_result["feedback"],
                error=None,
            )

        except Exception as e:
            return VerificationResult(
                score=0.0,
                passed=False,
                details={"error": str(e)},
                feedback=f"Verification failed: {e!s}",
                error=str(e),
            )

    def _extract_boxed_answer(self, text: Optional[str]) -> Optional[str]:
        """Extract answer from \\boxed{} notation."""
        if not text:
            return None

        boxed_pattern = r'\\boxed\s*{\s*([^}]+)\s*}'
        match = re.search(boxed_pattern, text)
        return match.group(1).strip() if match else None

    def _construct_verification_prompt(
        self, question: str, solution: str, answer: Optional[str]
    ) -> str:
        """Construct prompt for LLM verification."""
        prompt = (
            "Please verify this mathematical solution.\n\n"
            f"Question: {question}\n"
            f"Student's solution: {solution}\n"
        )

        if answer:
            prompt += f"Correct answer: {answer}\n"

        prompt += (
            "\nPlease verify if the solution is correct and provide feedback "
            "in the following JSON format:\n"
            "{\n"
            '  "score": <float between 0 and 1>,\n'
            '  "passed": <boolean>,\n'
            '  "details": {<relevant details>},\n'
            '  "feedback": "<explanation>"\n'
            "}"
        )

        return prompt

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into verification result."""
        try:
            # Basic parsing in practice you might want more robust JSON parsing
            import json

            result = json.loads(response)

            # Ensure required fields
            required_fields = ["score", "passed", "details", "feedback"]
            if not all(field in result for field in required_fields):
                raise ValueError("Missing required fields in LLM response")

            return result

        except Exception as e:
            return {
                "score": 0.0,
                "passed": False,
                "details": {"error": f"Failed to parse LLM response: {e!s}"},
                "feedback": "Error in LLM verification",
            }
