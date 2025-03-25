# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========

import json
import os
import random
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from camel.agents import ChatAgent
from camel.logger import get_logger

from .templates import EvolInstructTemplates

logger = get_logger(__name__)


class EvolInstructPipeline:
    r"""A pipeline for evolving prompts using the Evol-Instruct methodology.

    Args:
        agent (ChatAgent): The agent used to interact and generate
            instructions.
    """
    
    def __init__(
        self, 
        agent: ChatAgent,
    ):
        r"""Initializes the EvolInstructPipeline with an LLM agent.
        
        Args:
            agent (ChatAgent): The agent used for prompt evolution.
        """
        self.agent = agent if agent else ChatAgent()
    
    def _set_method(
        self, 
        method: Optional[Union[str, List[str]]] = "uniform",
        num_generations: int = 1,
    ) -> List[str]:
        r"""Sets the method to use for generating prompts for one iteration.
        
        Args:
        method (Optional[Union[str, List[str]]]): 
            The method(s) to use for evolving the prompt. Can be:
            - (list) a list of methods with length equal to num_generations.
            - (str) a single method in EvolInstructTemplates, or "uniform".
        num_generations: The number of variations to generate in one iteration.
        
        Returns:
            methods (list) The list of method to use for generating prompts.
        """
        # Case 1: user provides a list of methods
        if isinstance(method, list):
            
            if len(method) == num_generations:
                methods = [
                    i if i in EvolInstructTemplates.EVOL_METHODS else "uniform"
                    for i in method
                ]
                
            else:
                methods = ["uniform"] * num_generations
                logger.info("methods length not match; use uniform instead.")
        
        # Case 2: user provides a single method - broadcast w/ random selection    
        elif isinstance(method, str):
            if method in EvolInstructTemplates.EVOL_METHODS:  
                methods = [method] * num_generations
            
            elif method in ["in-breadth", "in-depth", "uniform"]:
                method_mapping = {
                    "in-breadth": EvolInstructTemplates.IN_BREADTH_KEYS,
                    "in-depth": EvolInstructTemplates.IN_DEPTH_KEYS,
                    "uniform": list(EvolInstructTemplates.EVOL_METHODS.keys()),
                }
                methods = [
                    random.choice(method_mapping[method]) 
                    for _ in range(num_generations)
                ]
                     
            else:
                logger.info(f"Invalid method: {method}. Set as uniform.")
                methods = ["uniform"] * num_generations

        else:
            raise ValueError("method must be a string or a list of methods.")
        
        return methods

    def _generate_single(
        self, 
        prompt: str,  # for a single prompt
        method: str = "uniform",
        return_method: bool = False,
    ) -> Union[str, Tuple[str, str]]:
        r"""Generates a single new prompt for a single seed prompt 
        using a specified method.
        
        Args:
            prompt (str): The input prompt to evolve.
            method (str): 
                The method(s) to use for evolving the prompt. Can be:
                - (str) a single method defined in EvolInstructTemplates.
                - (str) "uniform" for random selection.
        
        Returns:
            The evolved prompt as a string, optionally with the method
        """
        # Handle the case when using this method externally
        if method == "uniform":
            method = random.choice(
                list(EvolInstructTemplates.EVOL_METHODS.keys())
            )
        elif method == "in-depth":
            method = random.choice(EvolInstructTemplates.IN_DEPTH_KEYS)
        elif method == "in-breadth":
            method = random.choice(EvolInstructTemplates.IN_BREADTH_KEYS)

        # Choose the instruction template based on the method
        instruction = (
            EvolInstructTemplates.INST_IN_BREADTH 
            if method in EvolInstructTemplates.IN_BREADTH_KEYS
            else EvolInstructTemplates.INST_IN_DEPTH
        ).format(
            method=EvolInstructTemplates.EVOL_METHODS.get(
                method, 
                random.choice(
                    list(EvolInstructTemplates.EVOL_METHODS.values())
                )
            ),
            prompt=prompt,
        )
        
        # Generate new prompt using the agent
        self.agent.reset()
        response = self.agent.step(instruction)
        generated_prompt = response.msgs[0].content.strip()
        
        if not return_method:
            return generated_prompt
        else:
            return generated_prompt, method

    def _generate_multiple(
        self, 
        prompt: str,  # for a single prompt
        method: Union[str, List[str]] = "uniform", 
        num_generations: int = 2, 
        keep_original: bool = True,
    ) -> List[Tuple[str, str]]:
        r"""Generates multiple variations of a single seed prompt x.
        Note those variations are directly generated from the same seed,
        that is, [x_1, x_2, ..., x_N] <- LLM( | x, method), where N is width.
        
        Args:
            prompt (str): The input prompt to evolve.
            method (Union[str, List[str]]): 
                The method(s) to use for evolving the prompt. Can be:
                - A single method (str).
                - A list of methods with length equal to num_generations.
                - "uniform" for random selection.
            num_generations (int): Number of variations to generate.
            keep_original (bool): Whether to include the original in output.
        
        Returns:
            A list of tuples (evolved_prompt, method).
        """
        from concurrent.futures import ThreadPoolExecutor
        
        # initialize the results list for generated prompts
        results = [(prompt, "original")] if keep_original else []
        
        # set the method
        methods = self._set_method(
            method=method, 
            num_generations=num_generations,
        )

        # generate prompts concurrently
        def process_single(method):
            return self._generate_single(prompt, method), method
        
        with ThreadPoolExecutor() as executor:
            generated_results = list(executor.map(process_single, methods))

        results.extend(generated_results)
        
        return results
    
    def _generate_iter(
        self,
        prompt: str,  # for a single prompt
        method: Union[str, Dict[int, List[str]]] = "uniform", 
        num_generations: int = 1,
        num_evolutions: int = 1,
        keep_original: bool = True,
        scorer: str = "uniform"
    ) -> Dict[int, List[Tuple[str, str]]]:
        r"""Iteratively evolve a prompt over multiple generations.
        Note variations are iteratively generated from the previous prompt,
        i.e., [x_11, x_12, ..., x_1N] <- LLM( | x, method), where N is width.
        We then use a scorer to select one of the seed prompt 
        for the next iteration, say x_12,
        then, [x_21, x_22, ..., x_2W] <- LLM( | x_12, method), and so on.
        Here, the num_evolutions can be seen as the depth of the evolution. 
        We can call this as "TreeBoN", if we choose the best of N prompts 
        in each iteration.
        When N is 1, that is the default EvolInstruct setting.

        Args:
            prompt (str): The input prompt to evolve.
            method (Union[str, Dict[int, List[str]]]): 
                The method(s) to use for evolving the prompt. Can be:
                - "uniform" for random selection.
                - A dictionary mapping iteration numbers to lists of methods.
            num_generations (int): 
                The number of variations to generate in each iteration.
            num_evolutions (int): 
                The number of iterations to perform.
            keep_original (bool): 
                Whether to include the original prompt in the output of 
                each iteration.
            scorer: 
                The scoring method to select the best prompt 
                for the next iteration.
                For now, "uniform" assigns random scores.
        
        Returns:
            Dict[int, List[Tuple[str, str]]]:
                A dictionary where keys are iteration numbers,
                and values are lists of tuples (prompt, method).

        References:
            - eva: Evolving Alignment via Asymmetric Self-Play
              https://ziyu-deep.github.io/files/eva-arxiv.pdf 
              see appendix for details.
        """
        results = {}

        current_prompt = prompt

        for iteration in range(num_evolutions):
            # set the method for the current iteration
            if isinstance(method, dict):
                method = method.get(iteration, "uniform")

            # generate the batch for the current iteration
            batch_results = self._generate_multiple(
                prompt=current_prompt,
                method=method,
                num_generations=num_generations,
                keep_original=False,
            )

            if keep_original:
                batch_results.insert(0, (current_prompt, "original"))

            results[iteration] = batch_results

            # assign scores and select the best prompt for the next iteration
            if scorer == "uniform":
                # simulate random scores in range (1, 10) for now
                scores = (
                    [random.randint(1, 10) for _ in batch_results[1:]] 
                    if keep_original 
                    else [random.randint(1, 10) for _ in batch_results]
                )
            else:
                # TODO: implement instruction scoring module,
                # e.g., complexity/quality scorer or by reward advantage
                raise NotImplementedError(
                    f"Scorer '{scorer}' is not implemented."
                )

            # select the prompt with the highest score
            best_index = scores.index(max(scores))
            current_prompt = (
                batch_results[best_index + 1][0]
                if keep_original
                else batch_results[best_index][0]
            )


        return results

    def generate(
        self,
        prompts: List[str],
        method: Union[str, Dict[int, List[str]]] = "uniform",
        num_generations: int = 1,
        num_evolutions: int = 1,
        keep_original: bool = True,
        scorer: str = "uniform",
        num_chunks: int = 1, 
        retry_limit: int = 3,
        retry_delay: float = 30,  # in seconds
    ) -> List[Dict[int, List[Tuple[str, str]]]]:
        r"""Divide the list of prompts into chunks,
        iterate through each chunk sequentially,
        then process the prompts within each chunk in parallel

        Args:
            prompts (List[str]): A list of prompts to evolve.
            method (Union[str, Dict[int, List[str]]]):
                The method(s) to use for evolving the prompt. Can be:
                - "uniform" for random selection.
                - A dictionary mapping iteration numbers to lists of methods,
                  where each list has length equal to num_generations.
            num_generations (int): 
                The number of variations to generate in each iteration.
            num_evolutions (int): 
                The number of iterations to perform.
            keep_original (bool): 
                Whether to include the original prompt in the output of 
                each iteration.
            scorer (str): s
                The scoring method to select the best prompt for 
                the next iteration.
            num_chunks (int): 
                The number of chunks to process batch of prompts.
                specify a larger number of chunks to avoid hitting RPM limits 
                for API requests.
            retry_limit (int): maximum number of retries for failed requests.
            retry_delay (float): The delay between retries in seconds.

        Returns:
            List[Dict[int, List[Tuple[str, str]]]]:
            A list of dictionaries, where each dict corresponds to 
            results of one prompt.
        """
        from concurrent.futures import ThreadPoolExecutor
        from math import ceil

        def process_prompt(prompt):
            retries = 0
            while retries <= retry_limit:
                try:
                    return self._generate_iter(
                        prompt=prompt,
                        method=method,
                        num_generations=num_generations,
                        num_evolutions=num_evolutions,
                        keep_original=keep_original,
                        scorer=scorer,
                    )
                except Exception as e:
                    if retries < retry_limit:
                        logger.info(
                            f"Error: {e}. Retry in {retry_delay}s... "
                            f"(Attempt {retries + 1}/{retry_limit})"
                        )
                        time.sleep(retry_delay)
                        retries += 1
                    else:
                        logger.info(
                            f"Failed after {retry_limit} attempts: {e}"
                        )
                        return {i: [] for i in range(num_evolutions)}

        # split prompts into chunks
        num_chunks = max(1, min(num_chunks, len(prompts)))
        chunk_size = ceil(len(prompts) / num_chunks)
        chunks = [
            prompts[i: i + chunk_size] 
            for i in range(0, len(prompts), chunk_size)
        ]

        # generate prompts
        results = []
        for i, chunk in enumerate(chunks):
            logger.info(
                f"Processing chunk {i + 1}/{num_chunks} "
                f"with {len(chunk)} prompts..."
            )
            with ThreadPoolExecutor() as executor:
                chunk_results = list(executor.map(process_prompt, chunk))
                results.extend(chunk_results)

        return results
