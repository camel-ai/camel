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
from typing import Any, Dict, List, Optional, Tuple, Type, Union, cast

from tqdm import tqdm

from camel.agents import ChatAgent
from camel.datagen.base import BaseDataGenPipeline
from camel.datagen.evol_instruct.scorer import BaseScorer, GeneralScorer
from camel.datagen.evol_instruct.templates import EvolInstructTemplates
from camel.logger import get_logger

logger = get_logger(__name__)


class EvolInstructPipeline(BaseDataGenPipeline):
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
        output_path (Optional[str]): Path to save generated data.
            (default: :obj:`None`)
        save_intermediate (bool): Whether to save intermediate results.
            (default: :obj:`False`)
    """

    def __init__(
        self,
        templates: Type = EvolInstructTemplates,
        agent: Optional[ChatAgent] = None,
        output_path: Optional[str] = None,
        save_intermediate: bool = False,
    ) -> None:
        r"""Initialize pipeline with templates and language model agent.

        Args:
            templates (Type[EvolInstructTemplates]): Template class containing
                evolution strategy configurations.
                (default: :obj:`EvolInstructTemplates`)
            agent (Optional[ChatAgent]): Preconfigured chat agent instance.
                Creates a default ChatAgent if not provided.
                (default: :obj:`None`)
            output_path (Optional[str]): Path to save generated data.
                (default: :obj:`None`)
            save_intermediate (bool): Whether to save intermediate results.
                (default: :obj:`False`)
        """
        super().__init__(
            output_path=output_path,
            save_intermediate=save_intermediate,
        )
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
        prompts: Union[str, List[Dict[str, Any]], List[str]],
        evolution_spec: Union[str, List[Union[str, List[str]]]],
        num_generations: int = 2,
        num_iterations: Optional[int] = None,
        keep_original: bool = True,
        scorer: Optional[BaseScorer] = None,
        num_chunks: int = 1,
        retry_limit: int = 3,
        retry_delay: float = 1.0,
        num_threads: int = 10,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        r"""Generates evolved prompts from a set of seed prompts.

        Core implementation that performs the generation logic.

        This method supports flexible input formats:
        - File path to a JSONL file containing prompts
        - JSONL string
        - List of dictionaries with a 'prompt' field
        - List of prompt strings

        Args:
            prompts (Union[str, List[Dict[str, Any]], List[str]]):
                Source prompts. Can be a file path, JSONL string, list of
                dictionaries with 'prompt' field, or list of strings.
            evolution_spec (Union[str, List[Union[str, List[str]]]]):
                Evolution method specification.
                If a list is provided and num_iterations is None, then
                num_iterations is set to the length of the list.
            num_generations (int): Candidates to generate per iteration.
                (default: :obj:`2`)
            num_iterations (Optional[int]): Number of evolution iterations.
                Defaults to the length of evolution_spec.
            keep_original (bool): Include original prompts in results.
                (default: :obj:`True`)
            scorer (Optional[BaseScorer]): Scoring model for candidates.
                (default: :obj:`None`)
            num_chunks (int): Number of chunks to split processing.
                (default: :obj:`1`)
            retry_limit (int): Number of retries for failed generations.
                (default: :obj:`3`)
            retry_delay (float): Delay between retries in seconds.
                (default: :obj:`1.0`)
            num_threads (int): Number of threads for parallel processing.
                (default: :obj:`10`)
            **kwargs (Any): Additional keyword arguments.

        Returns:
            List[Dict[str, Any]]: Evolution results converted to
            standard format.
        """
        # Load data from various formats
        seed_prompts = []

        if isinstance(prompts, str):
            # Handle file path or JSONL string
            loaded_data = self.load_data(prompts)
            # Ensure loaded_data is properly typed
            processed_data: List[Dict[str, Any]] = []
            for item in loaded_data:
                if isinstance(item, dict):
                    processed_data.append(item)
                else:
                    processed_data.append({"prompt": item})

            for item in processed_data:
                if isinstance(item, dict) and 'prompt' in item:
                    seed_prompts.append(item['prompt'])
                elif isinstance(item, dict) and isinstance(
                    item.get('text', ''), str
                ):
                    seed_prompts.append(item.get('text', ''))
        elif isinstance(prompts, list):
            # Handle list of dicts or list of strings
            for prompt_item in prompts:
                if isinstance(prompt_item, dict) and 'prompt' in prompt_item:
                    seed_prompts.append(prompt_item['prompt'])
                elif isinstance(prompt_item, str):
                    seed_prompts.append(prompt_item)
                else:
                    logger.warning(
                        f"Skipping invalid prompt item: {prompt_item}"
                    )
        else:
            raise ValueError(
                "Prompts must be a file path, JSONL string, "
                "list of dictionaries with 'prompt' field, or list of strings"
            )

        logger.info(f"Loaded {len(seed_prompts)} prompts for evolution")

        # Original processing logic
        if num_iterations is None:
            if isinstance(evolution_spec, list):
                num_iterations = len(evolution_spec)
            else:
                num_iterations = 1

        evolution_plan: List[List[List[str]]] = []
        for _ in seed_prompts:
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
            current_prompt, method_plan = args
            retries = 0
            while retries <= retry_limit:
                try:
                    return self._generate_iterative_evolutions(
                        prompt=current_prompt,
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
                        # Return empty dict with proper type
                        return cast(Dict[int, List[Dict[str, Any]]], {})

            return cast(Dict[int, List[Dict[str, Any]]], {})

        num_chunks = max(1, min(num_chunks, len(seed_prompts)))
        chunk_size = len(seed_prompts) // num_chunks
        raw_results = []

        # Process each chunk of prompts
        for chunk_idx in range(0, len(seed_prompts), chunk_size):
            chunk = seed_prompts[chunk_idx : chunk_idx + chunk_size]
            plan_chunk = evolution_plan[chunk_idx : chunk_idx + chunk_size]

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                chunk_results = list(
                    tqdm(
                        executor.map(_process_prompt, zip(chunk, plan_chunk)),
                        total=len(chunk),
                    )
                )
                raw_results.extend(chunk_results)

                # Save intermediate results after each chunk if configured
                if chunk_idx > 0 and self.save_intermediate:
                    # Convert the partial results to the expected format
                    partial_results = []
                    for i, evol_result in enumerate(raw_results):
                        if i < len(seed_prompts):
                            seed_prompt = seed_prompts[i]
                        else:
                            seed_prompt = "unknown"

                        partial_results.append(
                            {
                                "seed_prompt": seed_prompt,
                                "evolutions": evol_result,
                                "metadata": {
                                    "num_iterations": num_iterations,
                                    "num_generations": num_generations,
                                },
                            }
                        )

                    # Call the hook for intermediate results
                    self.save_intermediate_results(partial_results)

        # Convert the results to the expected format for BaseDataGenPipeline
        standardized_results = []
        for i, evol_result in enumerate(raw_results):
            seed_prompt = (
                seed_prompts[i] if i < len(seed_prompts) else "unknown"
            )
            standardized_results.append(
                {
                    "seed_prompt": seed_prompt,
                    "evolutions": evol_result,
                    "metadata": {
                        "num_iterations": num_iterations,
                        "num_generations": num_generations,
                    },
                }
            )

        return standardized_results

    def execute(
        self,
        prompts: Union[str, List[Dict[str, Any]], List[str]],
        evolution_spec: Union[str, List[Union[str, List[str]]]],
        num_generations: int = 2,
        num_iterations: Optional[int] = None,
        keep_original: bool = True,
        scorer: Optional[BaseScorer] = None,
        num_chunks: int = 1,
        retry_limit: int = 3,
        retry_delay: float = 1.0,
        num_threads: int = 10,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        r"""Execute the Evol-Instruct pipeline.

        The main entry point for running the pipeline. Handles logging,
        time measurement, and result saving.

        Args:
            prompts: Source prompts.
                Can be a file path, JSONL string, list of dictionaries
                with 'prompt' field, or list of strings.
            evolution_spec (Union[str, List[Union[str, List[str]]]]):
                Evolution method specification.
                If a list is provided and num_iterations is None, then
                num_iterations is set to the length of the list.
            num_generations (int): Candidates to generate per iteration.
                (default: :obj:`2`)
            num_iterations (Optional[int]): Number of evolution iterations.
                Defaults to the length of evolution_spec.
            keep_original (bool): Include original prompts in results.
                (default: :obj:`True`)
            scorer (Optional[BaseScorer]): Scoring model for candidates.
                (default: :obj:`None`)
            num_chunks (int): Number of chunks to split processing.
                (default: :obj:`1`)
            retry_limit (int): Number of retries for failed generations.
                (default: :obj:`3`)
            retry_delay (float): Delay between retries in seconds.
                (default: :obj:`1.0`)
            num_threads (int): Number of threads for parallel processing.
                (default: :obj:`10`)

        Returns:
            List[Dict[str, Any]]: Standardized evolution results.
        """
        return super().execute(
            prompts=prompts,
            evolution_spec=evolution_spec,
            num_generations=num_generations,
            num_iterations=num_iterations,
            keep_original=keep_original,
            scorer=scorer,
            num_chunks=num_chunks,
            retry_limit=retry_limit,
            retry_delay=retry_delay,
            num_threads=num_threads,
            **kwargs,
        )
