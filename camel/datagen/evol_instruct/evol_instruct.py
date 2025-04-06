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

import random
import time
from concurrent.futures import ThreadPoolExecutor
from math import ceil
from typing import Any, Dict, List, Optional, Tuple, Type, Union, cast

from tqdm import tqdm

from camel.agents import ChatAgent
from camel.datagen.evol_instruct.scorer import BaseScorer, GeneralScorer
from camel.datagen.evol_instruct.templates import EvolInstructTemplates
from camel.logger import get_logger

logger = get_logger(__name__)


class EvolInstructPipeline:
    r"""Pipeline for evolving prompts using the Evol-Instruct methodology.

    Supports custom templates defining evolution strategies and methods. The
    pipeline leverages language models to iteratively refine prompts through
    specified evolution strategies.

    Args:
        templates (Type[EvolInstructTemplates]): Template class containing
            evolution strategy and method definitions. Must provide
            `EVOL_METHODS` and `STRATEGY` attributes.
            (default: :obj:`EvolInstructTemplates`)
        agent (Optional[ChatAgent]): Chat agent instance for LLM interaction.
            If :obj:`None`, initializes with a default ChatAgent.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        templates: Type = EvolInstructTemplates,
        agent: Optional[ChatAgent] = None,
    ) -> None:
        r"""Initialize pipeline with templates and language model agent.

        Args:
            templates (Type[EvolInstructTemplates]): Template class containing
                evolution strategy configurations.
                (default: :obj:`EvolInstructTemplates`)
            agent (Optional[ChatAgent]): Preconfigured chat agent instance.
                Creates a default ChatAgent if not provided.
                (default: :obj:`None`)
        """
        self.templates = templates
        self.agent = agent or ChatAgent()

    def _resolve_evolution_method(self, method_key: str) -> str:
        r"""Resolve evolution method key to concrete implementation.

        Args:
            method_key (str): Input method identifier. Can be:
                - Direct method key from templates.EVOL_METHODS
                - Strategy name from templates.STRATEGY keys

        Returns:
            str: Resolved method key from EVOL_METHODS
        """
        if method_key in self.templates.EVOL_METHODS:
            return method_key
        if method_key.upper() in self.templates.STRATEGY:
            strategy = self.templates.STRATEGY[method_key.upper()]
            strategy_methods = strategy["methods"]
            return random.choice(strategy_methods)

        logger.warning(
            f"Invalid evolution method: {method_key}. "
            f"Using random selection."
        )
        return random.choice(list(self.templates.EVOL_METHODS))

    def _get_evolution_methods(
        self,
        method: Union[str, List[str]],
        num_generations: int = 2,
    ) -> List[str]:
        r"""Get list of evolution methods based on input specification.

        Args:
            method (Union[str, List[str]]): Specification for method selection.
                Can be:
                - Strategy name for methods from that strategy
                - Specific method name
                - List of method specifications
            num_generations (int): Number of methods to return.

        Returns:
            List[str]: List of resolved method names
        """
        candidate_methods = []

        if isinstance(method, list):
            for method_spec in method:
                candidate_methods.append(
                    self._resolve_evolution_method(method_spec)
                )
        elif isinstance(method, str):
            if method.upper() in self.templates.STRATEGY:
                strategy = self.templates.STRATEGY[method.upper()]
                candidate_methods = strategy["methods"]
            else:
                candidate_methods = [self._resolve_evolution_method(method)]

        # Remove duplicates while preserving order
        unique_candidates = []
        for method_name in candidate_methods:
            if method_name not in unique_candidates:
                unique_candidates.append(method_name)

        if len(unique_candidates) >= num_generations:
            methods = random.sample(unique_candidates, num_generations)
        else:
            methods = unique_candidates.copy()
            while len(methods) < num_generations:
                methods.append(random.choice(unique_candidates))

        return methods

    def _generate_single_evolution(
        self,
        prompt: str,
        method: str,
        return_method: bool = False,
    ) -> Tuple[str, str]:
        r"""Generate a single evolved prompt from a seed prompt.

        Args:
            prompt (str): The seed prompt to evolve.
            method (str): The evolution method key to use.
            return_method (bool): If True, returns method along with prompt.

        Returns:
            Tuple[str, str]: Evolved prompt and method
        """
        resolved_method = self._resolve_evolution_method(method)

        # Find strategy containing the resolved method
        strategy_key = None
        for strategy, group in self.templates.STRATEGY.items():
            if resolved_method in group["methods"]:
                strategy_key = strategy
                break

        if strategy_key is None:
            strategy_key = random.choice(list(self.templates.STRATEGY.keys()))

        strategy = self.templates.STRATEGY[strategy_key]
        instruction_template = strategy["meta_instruction"]
        instruction = instruction_template.format(
            method=self.templates.EVOL_METHODS.get(
                resolved_method,
                random.choice(list(self.templates.EVOL_METHODS.values())),
            ),
            prompt=prompt,
        )

        self.agent.reset()
        response = self.agent.step(instruction)
        evolved_prompt = response.msgs[0].content.strip()

        if return_method:
            return (evolved_prompt, resolved_method)
        else:
            return (evolved_prompt, "")

    def _generate_multiple_evolutions(
        self,
        prompt: str,
        method: Union[str, List[str]],
        num_generations: int = 2,
        keep_original: bool = True,
        num_threads: int = 10,
    ) -> List[Tuple[str, str]]:
        r"""Generate multiple evolved versions of a prompt.

        Args:
            prompt (str): Seed prompt to evolve.
            method (Union[str, List[str]]): Evolution method specification.
            num_generations (int): Candidates to generate per iteration.
            keep_original (bool): Whether to keep the original prompt.
            num_threads (int): Number of threads for parallel processing.

        Returns:
            List[Tuple[str, str]]: List of (evolved_prompt, method) pairs
        """
        results = [(prompt, "original")] if keep_original else []

        if isinstance(method, list) and len(method) == num_generations:
            candidate_methods = method
        else:
            candidate_methods = self._get_evolution_methods(
                method=method, num_generations=num_generations
            )

        def _process_single_method(method_name: str) -> Tuple[str, str]:
            return self._generate_single_evolution(
                prompt, method_name, return_method=True
            )

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            evolved_results = list(
                executor.map(_process_single_method, candidate_methods)
            )

        results.extend(evolved_results)
        return results

    def _generate_iterative_evolutions(
        self,
        prompt: str,
        evolution_spec: Union[str, List[Union[str, List[str]]]],
        num_generations: int = 2,
        num_iterations: Optional[int] = None,
        keep_original: bool = True,
        scorer: Optional[BaseScorer] = None,
        num_threads: int = 10,
    ) -> Dict[int, List[Dict[str, Any]]]:
        r"""Generate iterative evolutions of a prompt with scoring.

        Args:
            prompt (str): Seed prompt to evolve.
            evolution_spec (Union[str, List[Union[str, List[str]]]]):
                Evolution method specification.
                If a list is provided and num_iterations is None, then
                num_iterations is set to the length of the list.
            num_generations (int): Candidates to generate per iteration.
            num_iterations (Optional[int]): Number of evolution iterations.
                Defaults to the length of evolution_spec.
            keep_original (bool): Include original prompt in results.
            scorer (Optional[BaseScorer]): Scoring model for candidate.
            num_threads (int): Number of threads for parallel processing.

        Returns:
            Dict[int, List[Dict[str, Any]]]: Evolution results per iteration,
                where each candidate is represented as a dict with keys:
                "instruction", "method", and "scores".
        """
        if num_iterations is None:
            if isinstance(evolution_spec, list):
                num_iterations = len(evolution_spec)
            else:
                num_iterations = 1

        results = {}
        current_prompt = prompt
        scorer = scorer or GeneralScorer()

        for iteration in range(num_iterations):
            if isinstance(evolution_spec, list):
                if iteration < len(evolution_spec):
                    iteration_spec = evolution_spec[iteration]
                else:
                    iteration_spec = evolution_spec[-1]
            else:
                iteration_spec = evolution_spec

            batch_results = self._generate_multiple_evolutions(
                prompt=current_prompt,
                method=iteration_spec,
                num_generations=num_generations,
                keep_original=False,
                num_threads=num_threads,
            )

            scored_results = []
            for candidate, method_used in batch_results:
                scores = scorer.score(current_prompt, candidate)
                scored_results.append(
                    {
                        "instruction": candidate,
                        "method": method_used,
                        "scores": scores,
                    }
                )

            best_index = max(
                range(len(scored_results)),
                key=lambda i: sum(
                    cast(Dict[str, int], scored_results[i]["scores"]).values()
                ),
            )

            best_candidate = cast(
                str, scored_results[best_index]["instruction"]
            )

            if keep_original:
                results[iteration] = [
                    {
                        "instruction": current_prompt,
                        "method": "original",
                        "scores": {},
                    },
                    *scored_results,
                ]
            else:
                results[iteration] = scored_results

            current_prompt = best_candidate

        return results

    def generate(
        self,
        prompts: List[str],
        evolution_spec: Union[str, List[Union[str, List[str]]]],
        num_generations: int = 2,
        num_iterations: Optional[int] = None,
        keep_original: bool = True,
        scorer: Optional[BaseScorer] = None,
        num_chunks: int = 1,
        retry_limit: int = 3,
        retry_delay: float = 1.0,
        num_threads: int = 10,
    ) -> List[Dict[int, List[Dict[str, Any]]]]:
        r"""Evolve a batch of prompts through iterative refinement.

        Args:
            prompts (List[str]): Seed prompts to evolve.
            evolution_spec (Union[str, List[Union[str, List[str]]]]):
                Evolution method specification.
                If a list is provided and num_iterations is None, then
                num_iterations is set to the length of the list.
            num_generations (int): Candidates to generate per iteration.
            num_iterations (Optional[int]): Number of evolution iterations.
                Defaults to the length of evolution_spec.
            keep_original (bool): Include original prompts in results.
            scorer (Optional[BaseScorer]): Scoring model for candidate.
            num_chunks (int): Number of parallel processing chunks.
            retry_limit (int): Max retries for failed generations.
            retry_delay (float): Delay between retries in seconds.
            num_threads (int): Number of threads for parallel processing.

        Returns:
            List[Dict[int, List[Dict[str, Any]]]]: Evolution results.
        """
        if num_iterations is None:
            if isinstance(evolution_spec, list):
                num_iterations = len(evolution_spec)
            else:
                num_iterations = 1

        evolution_plan: List[List[List[str]]] = []
        for _ in prompts:
            prompt_plan = []
            for iteration in range(num_iterations):
                if isinstance(evolution_spec, list):
                    if iteration < len(evolution_spec):
                        raw_spec = evolution_spec[iteration]
                    else:
                        raw_spec = evolution_spec[-1]
                else:
                    raw_spec = evolution_spec
                prompt_plan.append(
                    self._get_evolution_methods(raw_spec, num_generations)
                )
            evolution_plan.append(prompt_plan)

        def _process_prompt(
            args: Tuple[str, List[List[str]]],
        ) -> Dict[int, List[Dict[str, Any]]]:
            prompt, methods = args
            retries = 0
            while retries <= retry_limit:
                try:
                    return self._generate_iterative_evolutions(
                        prompt=prompt,
                        evolution_spec=evolution_spec,
                        num_generations=num_generations,
                        num_iterations=num_iterations,
                        keep_original=keep_original,
                        scorer=scorer,
                        num_threads=num_threads,
                    )
                except Exception as e:
                    retries += 1
                    if retries <= retry_limit:
                        logger.warning(
                            f"Error processing prompt "
                            f"(attempt {retries}/{retry_limit}): {e!s}"
                        )
                        time.sleep(retry_delay)
                    else:
                        logger.error("Failed to process prompt.")
                        return {}

            raise RuntimeError("_process_prompt() did not return.")

        num_chunks = max(1, min(num_chunks, len(prompts)))
        chunk_size = ceil(len(prompts) / num_chunks)
        results = []

        for chunk_idx in range(0, len(prompts), chunk_size):
            chunk = prompts[chunk_idx : chunk_idx + chunk_size]
            plan_chunk = evolution_plan[chunk_idx : chunk_idx + chunk_size]

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                chunk_results = list(
                    tqdm(
                        executor.map(_process_prompt, zip(chunk, plan_chunk)),
                        total=len(chunk),
                    )
                )
                results.extend(chunk_results)

        return results
