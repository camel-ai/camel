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
from typing import Any

from camel.prompts import TextPrompt, TextPromptDict
from camel.types import RoleType


# flake8: noqa :E501
class GenerateTextEmbeddingDataPromptTemplateDict(TextPromptDict):
    r"""A :obj:`TextPrompt` dictionary containing text embedding tasks
    generation, query, positive and hard negative samples generation,
    from the `"Improving Text Embeddings with Large Language Models"
    <https://arxiv.org/abs/2401.00368>`_ paper.


    Attributes:
        GENERATE_TASKS (TextPrompt): A prompt to generate a list
            of :obj:`num_tasks` synthetic text_embedding tasks.
        ASSISTANT_PROMPT (TextPrompt): A system prompt for the AI assistant
            to generate synthetic :obj:`user_query`, :obj:`positive document`,
            and :obj:`hard_negative_document` for a specific :obj:`task` with
            specified parameters including :obj:`query_type`,
            :obj:`query_length`, :obj:`clarity`, :obj:`num_words`,
            :obj:`language` and :obj:`difficulty`.
    """

    GENERATE_TASKS = TextPrompt(
        """You are an expert to brainstorm a list of {num_tasks} potentially useful text retrieval tasks
Here are a few examples for your reference:
  - Provided a scientific claim as query, retrieve documents that help verify or refute the claim.
  - Search for documents that answers a FAQ-style query on children's nutrition.
Please adhere to the following guidelines:
  - Specify what the query is, and what the desired documents are.
  - Each retrieval task should cover a wide range of queries, and should not be too specific.
Your output should always be a python list of strings starting with `1.`, `2.` etc.
And each element corresponds to a distinct retrieval task in one sentence.
Do not explain yourself or output anything else.
Be creative!"""
    )

    ASSISTANT_PROMPT = TextPrompt(
        """You have been assigned a retrieval task: {task}
Your mission is to write one text retrieval example for this task in JSON format. The JSON object must
contain the following keys:
  - "user_query": a string, a random user search query specified by the retrieval task.
  - "positive_document": a string, a relevant document for the user query.
  - "hard_negative_document": a string, a hard negative document that only appears relevant to the query.
Please adhere to the following guidelines:
  - The "user_query" should be {query_type}, {query_length}, {clarity}, and diverse in topic.
  - All documents must be created independent of the query. Avoid copying the query verbatim.
It's acceptable if some parts of the "positive_document" are not topically related to the query.
  - All documents should be at least {num_words} words long.
  - The "hard_negative_document" contains some useful information, but it should be less useful or comprehensive compared to the "positive_document".
  - Both the query and documents should be in {language}.
  - Do not provide any explanation in any document on why it is relevant or not relevant to the query.
  - Both the query and documents require {difficulty} level education to understand.
Your output must always be a JSON object only (starting and ending with curly brackets), do not explain yourself or output anything else. Be creative!"""
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update(
            {
                "generate_tasks": self.GENERATE_TASKS,
                RoleType.ASSISTANT: self.ASSISTANT_PROMPT,
            }
        )
