# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
#
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
# ===========================================================================
from enum import Enum


class RoleType(Enum):
    ASSISTANT = "assistant"
    USER = "user"
    CRITIC = "critic"
    DEFAULT = "default"


class ModelType(Enum):
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"
    GPT_4_32k = "gpt-4-32k"


class TaskType(Enum):
    AI_SOCIETY = "ai_society"
    CODE = "code"
    MISALIGNMENT = "misalignment"
    TRANSLATION = "translation"
    EVALUATION = "evaluation"
    SOLUTION_EXTRACTION = "solution_extraction"
    DEFAULT = "default"


__all__ = ['RoleType', 'ModelType', 'TaskType']
