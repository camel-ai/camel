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

import unittest
from typing import Any, ClassVar, Dict
from unittest.mock import MagicMock, patch

from camel.agents import ChatAgent
from camel.datagen.evol_instruct import EvolInstructPipeline


# Dummy template class providing EVOL_METHODS and STRATEGY configuration.
class DummyTemplates:
    EVOL_METHODS: ClassVar[Dict[str, str]] = {
        "method1": "Method1 instruction",
        "method2": "Method2 instruction",
        "method3": "Method3 instruction",
    }
    STRATEGY: ClassVar[Dict[str, Dict[str, Any]]] = {
        "DEPTH": {
            "meta_instruction": "Use {method} to evolve: {prompt}",
            "methods": ["method1", "method2"],
        },
        "BREADTH": {
            "meta_instruction": "Apply {method} for expansion: {prompt}",
            "methods": ["method3"],
        },
    }


# Dummy scorer for testing purposes.
class DummyScorer:
    def score(self, current_prompt: str, candidate: str) -> Dict[str, int]:
        # Score based on the length of the candidate prompt.
        return {"score": len(candidate)}


class TestEvolInstructPipeline(unittest.TestCase):
    def setUp(self):
        # Create a mocked ChatAgent.
        self.mock_agent = MagicMock(spec=ChatAgent)
        self.mock_agent.reset.return_value = None
        # Simulate agent.step returning a response.
        fake_response = MagicMock()
        fake_response.msgs = [MagicMock(content="Evolved prompt")]
        self.mock_agent.step.return_value = fake_response

        self.templates = DummyTemplates
        self.pipeline = EvolInstructPipeline(
            templates=self.templates, agent=self.mock_agent
        )

    def test_resolve_evolution_method_direct(self):
        # When a key in EVOL_METHODS is provided,
        # it should return the key directly.
        self.assertEqual(
            self.pipeline._resolve_evolution_method("method1"), "method1"
        )

    def test_resolve_evolution_method_strategy(self):
        # When a strategy name is provided,
        # it should return one of the methods from that strategy.
        with patch("random.choice", return_value="method2") as mock_choice:
            resolved = self.pipeline._resolve_evolution_method("DEPTH")
            self.assertEqual(resolved, "method2")
            mock_choice.assert_called_once()

    def test_resolve_evolution_method_invalid(self):
        # When an invalid method is provided,
        # it should return a random valid method.
        with patch("random.choice", return_value="method1") as mock_choice:
            resolved = self.pipeline._resolve_evolution_method("invalid")
            self.assertEqual(resolved, "method1")
            mock_choice.assert_called_once()

    def test_get_evolution_methods_str(self):
        # When method is a strategy name,
        # it should return the strategy's defined methods.
        methods = self.pipeline._get_evolution_methods("DEPTH", 2)
        self.assertTrue(set(methods).issubset({"method1", "method2"}))
        self.assertEqual(len(methods), 2)

    def test_get_evolution_methods_list(self):
        # When method is a list,
        # it should return the parsed methods and sample to the number.
        methods = self.pipeline._get_evolution_methods(
            ["BREADTH", "method1"], 3
        )
        self.assertEqual(len(methods), 3)
        self.assertTrue(all(m in {"method1", "method3"} for m in methods))

    def test_generate_single_evolution(self):
        prompt = "Original prompt"
        # Test _generate_single_evolution returns an evolved prompt and method.
        evolved_prompt, method_used = self.pipeline._generate_single_evolution(
            prompt, "method1", return_method=True
        )
        expected_instruction = (
            "Use Method1 instruction to evolve: " "Original prompt"
        )
        self.mock_agent.reset.assert_called()  # Check that reset was called.
        self.mock_agent.step.assert_called_with(expected_instruction)
        self.assertEqual(evolved_prompt, "Evolved prompt")
        self.assertEqual(method_used, "method1")

    def test_generate_multiple_evolutions_keep_original(self):
        prompt = "Test prompt"
        results = self.pipeline._generate_multiple_evolutions(
            prompt,
            "DEPTH",
            num_generations=2,
            keep_original=True,
            num_threads=1,
        )
        # When keep_original is True,
        # the first result should be the original prompt.
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0][0], "Test prompt")
        self.assertEqual(results[0][1], "original")

    def test_generate_multiple_evolutions_no_original(self):
        prompt = "Test prompt"
        results = self.pipeline._generate_multiple_evolutions(
            prompt,
            "DEPTH",
            num_generations=2,
            keep_original=False,
            num_threads=1,
        )
        self.assertEqual(len(results), 2)

    def test_generate_iterative_evolutions(self):
        prompt = "Start prompt"
        scorer = DummyScorer()
        # evolution_spec as a list, with two iterations:
        # first DEPTH, then BREADTH.
        results = self.pipeline._generate_iterative_evolutions(
            prompt,
            evolution_spec=["DEPTH", "BREADTH"],
            num_generations=2,
            num_iterations=2,
            keep_original=True,
            scorer=scorer,
            num_threads=1,
        )
        # Check the number of iterations.
        self.assertEqual(len(results), 2)
        # The first element of each iteration should be the original prompt
        # or the best candidate.
        self.assertEqual(results[0][0]["instruction"], "Start prompt")
        self.assertIsInstance(results[1][0]["instruction"], str)

    def test_generate_batch(self):
        # Test the generate method handling multiple prompts.
        prompts = ["Prompt 1", "Prompt 2"]
        # To ensure test stability, patch _generate_iterative_evolutions to
        # return a fixed result.
        dummy_result = {
            0: [
                {
                    "instruction": "Evo",
                    "method": "method1",
                    "scores": {"score": 10},
                }
            ]
        }
        with patch.object(
            self.pipeline,
            "_generate_iterative_evolutions",
            return_value=dummy_result,
        ) as mock_iter:
            results = self.pipeline.generate(
                prompts,
                "DEPTH",
                num_generations=2,
                num_iterations=1,
                keep_original=False,
                num_threads=1,
            )
            self.assertEqual(len(results), 2)
            for res in results:
                self.assertEqual(res, dummy_result)
            self.assertEqual(mock_iter.call_count, len(prompts))


if __name__ == "__main__":
    unittest.main()
