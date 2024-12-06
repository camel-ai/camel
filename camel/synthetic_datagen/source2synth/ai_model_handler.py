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
from typing import List, Optional
from camel.synthetic_datagen.source2synth.models import MultiHopQA, ContextPrompt

from camel import logger
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.synthetic_datagen.source2synth.user_data_processor_config import (
    ProcessorConfig,
)
from camel.types import ModelPlatformType, ModelType

logger = logger.get_logger(__name__)


class AIModelHandler:
    """AI Model Processor"""

    def __init__(self, config: ProcessorConfig):
        self.config = config
        if config.use_ai_model:
            self.model = self._init_model()

    def _init_model(self):
        """Initialize AI model"""
        try:
            return ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O_MINI,
                model_config_dict={
                    "temperature": self.config.model_temperature,
                    "max_tokens": self.config.max_tokens,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to initialize AI model: {e!s}")
            return None

    def _init_agent(self):
        """Initialize AI agent"""
        if not self.model:
            return None

        # system_message =

        return ChatAgent(
            system_message=system_message,
            model=self.model,
            message_window_size=10,
        )

    def generate_qa_pair(
        self, context: str, related_contexts: List[str] = None
    ) -> Optional[MultiHopQA]:
        """Generate multi-hop question-answer pair using AI"""
        if not self.agent:
            return None

        try:
            # Construct a prompt containing multiple related contexts
            context_prompt = ContextPrompt(
                main_context=context,
                related_contexts=related_contexts
            )

            prompt = f"""{context_prompt}
            Generate a multi-hop question-answer pair that requires reasoning across multiple pieces of information.
            The question should require at least 2-3 logical steps to answer.
            Include the reasoning steps and supporting facts in your response.

            Format your response as:
            Question: [your question]
            Reasoning Steps:
            1. [step 1]
            2. [step 2]
            3. [step 3]
            Answer: [your answer]
            Supporting Facts: [relevant text segments]
            """

            # Get AI response
            response = self.agent.step(prompt)
            content = response.msgs[0].content

            # Parse response
            lines = content.strip().split('\n')
            question = None
            reasoning_steps = []
            answer = None
            supporting_facts = []

            current_section = None
            for line in lines:
                line = line.strip()
                if line.startswith('Question:'):
                    question = line[9:].strip()
                    current_section = 'question'
                elif line.startswith('Reasoning Steps:'):
                    current_section = 'reasoning'
                elif line.startswith('Answer:'):
                    answer = line[7:].strip()
                    current_section = 'answer'
                elif line.startswith('Supporting Facts:'):
                    current_section = 'facts'
                elif (
                    line
                    and current_section == 'reasoning'
                    and line[0].isdigit()
                ):
                    reasoning_steps.append(line[2:].strip())
                elif line and current_section == 'facts':
                    supporting_facts.append(line)

            if question and answer and reasoning_steps:
                return MultiHopQA(
                    question=question,
                    reasoning_steps=[ReasoningStep(step=step) for step in reasoning_steps],
                    answer=answer,
                    supporting_facts=supporting_facts
                )

        except Exception as e:
            logger.warning(
                f"Error generating multi-hop question-answer pair: {e!s}"
            )

        return None
