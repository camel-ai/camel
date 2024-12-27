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
from typing import Any, Callable, Dict

from .filter_function import (
    FilterFunction,
    KeywordFilter,
    LengthFilter,
    NonEnglishFilter,
    PunctuationFilter,
    RewardModelFilter,
    RougeSimilarityFilter,
)

FILTER_REGISTRY: Dict[str, Callable[[Dict[str, Any]], FilterFunction]] = {
    "length": lambda kwargs: LengthFilter(
        min_len=kwargs.get("min_len", 5), max_len=kwargs.get("max_len", 200)
    ),
    "keyword": lambda kwargs: KeywordFilter(
        keywords=kwargs.get("keywords", ["image", "data"])
    ),
    "punctuation": lambda kwargs: PunctuationFilter(),
    "non_english": lambda kwargs: NonEnglishFilter(),
    "rouge_similarity": lambda kwargs: RougeSimilarityFilter(
        existing_instructions=kwargs.get("existing_instructions", []),
        threshold=kwargs.get("threshold", 0.7),
    ),
    "reward": lambda kwargs: RewardModelFilter(
        reward_model=kwargs.get("reward_model"),  # type:ignore[arg-type]
        threshold=kwargs.get("threshold", 0.7),
    ),
}


def register_filter(
    name: str, constructor: Callable[[Dict[str, Any]], FilterFunction]
):
    r"""Registers a new filter constructor in FILTER_REGISTRY.

    Args:
        name (str): Unique name of the filter.
        constructor (Callable[[Dict[str, Any]], FilterFunction]): Function to
            create the filter using a dictionary of parameters.
    """
    FILTER_REGISTRY[name] = constructor
