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
from enum import Enum
import abc

from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class Document:
    r"""Class representing a document in the CAMEL chat system.

    Attributes:
        page_content (str): The main content of the document.
        metadata (dict): A dictionary containing metadata associated with the document.
    """
    page_content: str
    metadata: Dict[str, str] = field(default_factory=dict)


class RoleType(Enum):
    r"""Class representing various role types in the CAMEL chat system.

    Attributes:
        ASSISTANT (str): Represents the assistant role.
        USER (str): Represents the user role.
        CRITIC (str): Represents the critic role.
        DEFAULT (str): Represents the default role.
    """
    ASSISTANT = "assistant"
    USER = "user"
    CRITIC = "critic"
    EMBODIMENT = "embodiment"
    DEFAULT = "default"


class ModelType(Enum):
    r"""Class representing different models used in the CAMEL chat system.

    Attributes:
        GPT_3_5_TURBO (str): Represents the GPT-3.5-Turbo model.
        GPT_4 (str): Represents the GPT-4 model.
        GPT_4_32k (str): Represents the GPT-4-32k model.
    """
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"
    GPT_4_32k = "gpt-4-32k"


class TaskType(Enum):
    r"""Class representing various task types for the CAMEL chat system.

    Attributes:
        AI_SOCIETY (str): Represents the AI society task.
        CODE (str): Represents the coding task.
        MISALIGNMENT (str): Represents the misalignment task.
        TRANSLATION (str): Represents the translation task.
        EVALUATION (str): Represents the evaluation task.
        SOLUTION_EXTRACTION (str): Represents the solution extraction task.
        DEFAULT (str): Represents the default task.
    """
    AI_SOCIETY = "ai_society"
    CODE = "code"
    MISALIGNMENT = "misalignment"
    TRANSLATION = "translation"
    EVALUATION = "evaluation"
    SOLUTION_EXTRACTION = "solution_extraction"
    DEFAULT = "default"


__all__ = ['RoleType', 'ModelType', 'TaskType', 'Document']
