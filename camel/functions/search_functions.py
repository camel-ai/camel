# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import os
from typing import Any, Dict, List

import wikipedia

from .openai_function import OpenAIFunction


def search_wiki(entity: str) -> str:
    r"""Search the entity in WikiPedia and return the summary of the
    required page, containing factual information about the given entity.

    Args:
        entity (string): The entity to be searched.

    Returns:
        string: The search result. If the page corresponding to the entity
            exists, return the summary of this entity in a string.
    """
    result: str

    try:
        result = wikipedia.summary(entity, sentences=5, auto_suggest=False)
    except wikipedia.exceptions.DisambiguationError as e:
        result = wikipedia.summary(e.options[0], sentences=5,
                                   auto_suggest=False)
    except wikipedia.exceptions.PageError:
        result = ("There is no page in Wikipedia corresponding to entity "
                  f"{entity}, please specify another word to describe the"
                  " entity to be searched.")
    except wikipedia.exceptions.WikipediaException as e:
        result = f"An exception occurred during the search: {e}"

    return result


SEARCH_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func)
    for func in [search_wiki, search_google_and_summarize]
]
