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
from typing import Any, Dict, List

from .filter_function import FilterFunction, RewardModelFilter
from .filter_registry import FILTER_REGISTRY


class InstructionFilter:
    def __init__(self, filters_config: Dict[str, Dict[str, Any]]):
        r"""Initialize the InstructionFilter with a dictionary of filter
            configurations.

        Args:
            filters_config(Dict[str, Dict[str, Any]]):
                Example filters_config:
                {
                    "length": {"min_len": 5, "max_len": 100},
                    "keyword": {"keywords": ["image", "video"]},
                    "non_english": {},
                    "rouge_similarity": {
                        "existing_instructions": ["Some existing text"],
                        "threshold": 0.6
                    }
                }
                Each key in filters_config corresponds to a filter name
                    (registered in FILTER_REGISTRY).
                Each value is a dict of parameters for that filter.
        """
        self.filters: List[FilterFunction] = []
        for filter_name, params in filters_config.items():
            if filter_name not in FILTER_REGISTRY:
                raise ValueError(f"Unknown filter function: {filter_name}")
            self.filters.append(FILTER_REGISTRY[filter_name](params))

    def add_filter(self, filter_function: FilterFunction):
        r"""Add a custom filter function to the InstructionFilter.
        This allows adding filters that are not in the registry.

        Args:
            filter_function (FilterFunction): The filter function to be added
        """
        self.filters.append(filter_function)

    def filter(
        self, prompt: str, instruction: str, return_details: bool = False
    ):
        r"""Check if the given instruction passes all filter functions.

        Args:
            prompt (str): The prompt of generating the instruction.
            instruction (str): The instruction to evaluate.
            return_details (bool): If True, returns a tuple (bool, List[str])
                where the list contains the names of filters that failed.
                (default::obj:`False`)

        Returns:
            bool: True if the instruction passes all filters, False otherwise.
                OR (bool, List[str]) if return_details is True.
        """
        failed_filters = []
        for f in self.filters:
            if isinstance(f, RewardModelFilter):
                f.prompt = prompt
            if not f.apply(instruction):
                failed_filters.append(type(f).__name__)

        if return_details:
            return len(failed_filters) == 0, failed_filters
        return len(failed_filters) == 0
