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
from camel.prompts.ai_society import AISocietyPromptTemplateDict
from camel.prompts.base import CodePrompt, TextPrompt, TextPromptDict
from camel.prompts.code import CodePromptTemplateDict
from camel.prompts.evaluation import EvaluationPromptTemplateDict
from camel.prompts.misalignment import MisalignmentPromptTemplateDict
from camel.prompts.prompt_templates import PromptTemplateGenerator
from camel.prompts.solution_extraction import (
    SolutionExtractionPromptTemplateDict,
)
from camel.prompts.task_prompt_template import TaskPromptTemplateDict
from camel.prompts.translation import TranslationPromptTemplateDict

__all__ = [
    'TextPrompt',
    'CodePrompt',
    'TextPromptDict',
    'AISocietyPromptTemplateDict',
    'CodePromptTemplateDict',
    'MisalignmentPromptTemplateDict',
    'TranslationPromptTemplateDict',
    'EvaluationPromptTemplateDict',
    'TaskPromptTemplateDict',
    'PromptTemplateGenerator',
    'SolutionExtractionPromptTemplateDict',
]
