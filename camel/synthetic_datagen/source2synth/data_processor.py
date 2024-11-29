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
import logging
import os
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ProcessorConfig:
    """Data processing configuration class"""

    seed: int = 42  # Random seed
    min_length: int = 50  # Minimum text length
    max_length: int = 512  # Maximum text length
    quality_threshold: float = 0.7  # Quality threshold
    complexity_threshold: float = 0.5  # Complexity threshold
    dataset_size: int = 1000  # Target dataset size
    use_ai_model: bool = True  # Use AI model or not
    model_temperature: float = 0.4  # AI model temperature
    max_tokens: int = 4096  # Maximum tokens for AI model


class AIModelHandler:
    """AI Model Processor"""

    def __init__(self, config: ProcessorConfig):
        self.config = config
        if config.use_ai_model:
            self.model = self._init_model()
            self.agent = self._init_agent()

    def _init_model(self):
        """Initialize AI model"""
        try:
            return ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
                model_type="deepseek-chat",
                api_key=os.environ.get("OPENAI_COMPATIBILIY_API_KEY"),
                url=os.environ.get("OPENAI_COMPATIBILIY_API_BASE_URL"),
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

        system_message = """You are an expert at generating multi-hop question-answer pairs.
        For each context, you should:
        1. Identify multiple related facts or pieces of information
        2. Create questions that require reasoning across these multiple pieces
        3. Ensure the reasoning chain is clear and logical
        4. Generate questions that require at least 2-3 steps of reasoning
        5. Include the reasoning steps in the answer

        Format your response as:
        Question: [Complex question requiring multiple reasoning steps]
        Reasoning Steps:
        1. [First reasoning step]
        2. [Second reasoning step]
        3. [Final reasoning step]
        Answer: [Final answer]
        Supporting Facts: [List of relevant text segments used]
        """

        return ChatAgent(
            system_message=system_message,
            model=self.model,
            message_window_size=10,
        )

    def generate_qa_pair(
        self, context: str, related_contexts: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate multi-hop question-answer pair using AI"""
        if not self.agent:
            return None

        try:
            # Construct a prompt containing multiple related contexts
            context_prompt = f"Main Context: {context}\n"
            if related_contexts:
                context_prompt += "\nRelated Contexts:\n"
                for i, rel_ctx in enumerate(related_contexts, 1):
                    context_prompt += f"{i}. {rel_ctx}\n"

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
                return {
                    'question': question,
                    'reasoning_steps': reasoning_steps,
                    'answer': answer,
                    'supporting_facts': supporting_facts,
                    'type': 'multi_hop_qa',
                }

        except Exception as e:
            logger.warning(
                f"Error generating multi-hop question-answer pair: {e!s}"
            )

        return None


class UserDataProcessor:
    """User Data Processor"""

    def __init__(self, config: ProcessorConfig = None):
        self.config = config or ProcessorConfig()
        random.seed(self.config.seed)
        np.random.seed(self.config.seed)
        self.ai_handler = (
            AIModelHandler(self.config) if self.config.use_ai_model else None
        )

    def process_text(
        self, text: str, source: str = "user_input"
    ) -> List[Dict[str, Any]]:
        """Process a single text"""
        # Convert text to standard format
        raw_data = [
            {
                'text': text,
                'source': source,
                'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
        ]

        # Construct examples
        constructor = ExampleConstructor(self.config, self.ai_handler)
        examples = constructor.construct_examples(raw_data)

        # Manage data
        curator = DataCurator(self.config)
        final_dataset = curator.curate_dataset(examples)

        return final_dataset

    def process_batch(
        self, texts: List[str], sources: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Process multiple texts in batch"""
        if sources is None:
            sources = ["user_input"] * len(texts)
        elif len(sources) != len(texts):
            raise ValueError("Length of sources must match length of texts")

        raw_data = [
            {
                'text': text,
                'source': source,
                'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            for text, source in zip(texts, sources)
        ]

        # Construct examples
        constructor = ExampleConstructor(self.config, self.ai_handler)
        examples = constructor.construct_examples(raw_data)

        # Manage data
        curator = DataCurator(self.config)
        final_dataset = curator.curate_dataset(examples)

        return final_dataset


class ExampleConstructor:
    """Example Constructor"""

    def __init__(
        self,
        config: ProcessorConfig,
        ai_handler: Optional[AIModelHandler] = None,
    ):
        self.config = config
        self.ai_handler = ai_handler

    def construct_examples(
        self, raw_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Construct training examples"""
        logger.info("Starting to construct training examples...")
        examples = []

        for data in tqdm(raw_data, desc="Constructing examples"):
            try:
                # 1. Text preprocessing
                processed_text = self._preprocess_text(data.get('text', ''))
                if not processed_text:
                    continue

                # 2. Generate key information pairs
                info_pairs = self._extract_info_pairs(processed_text)

                # 3. Construct question-answer pairs
                qa_pairs = self._generate_qa_pairs(info_pairs)

                # 4. Add metadata
                example = {
                    'text': processed_text,
                    'qa_pairs': qa_pairs,
                    'metadata': {
                        'source': data.get('source', 'unknown'),
                        'timestamp': data.get('timestamp', ''),
                        'complexity': self._calculate_complexity(qa_pairs),
                    },
                }

                examples.append(example)

            except Exception as e:
                logger.warning(f"Error constructing example: {e!s}")
                continue

        logger.info(f"Successfully constructed {len(examples)} examples")
        return examples

    def _preprocess_text(self, text: str) -> str:
        """Text preprocessing"""
        if not isinstance(text, str):
            return ''

        # 1. Basic cleaning
        text = text.strip()

        # 2. Length check
        if (
            len(text) < self.config.min_length
            or len(text) > self.config.max_length
        ):
            return ''

        # 3. Quality check
        if not self._check_text_quality(text):
            return ''

        return text

    def _check_text_quality(self, text: str) -> bool:
        """Check text quality"""
        # 1. Basic quality check
        if text.count('.') < 2:  # Must have at least 2 sentences
            return False

        # 2. Special character ratio check
        special_char_ratio = len(
            [c for c in text if not c.isalnum() and not c.isspace()]
        ) / len(text)
        if special_char_ratio > 0.3:  # No more than 30% special characters
            return False

        return True

    def _extract_info_pairs(self, text: str) -> List[Dict[str, str]]:
        """Extract information pairs and relationships"""
        # Split into sentences
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        info_pairs = []

        # Extract combinations of multiple related sentences
        for i in range(len(sentences) - 2):
            if len(sentences[i]) > 10 and len(sentences[i + 1]) > 10:
                info_pairs.append(
                    {
                        'premise': sentences[i],
                        'intermediate': sentences[i + 1],
                        'conclusion': sentences[i + 2]
                        if i + 2 < len(sentences)
                        else '',
                        'related_contexts': [
                            s
                            for j, s in enumerate(sentences)
                            if j != i and j != i + 1 and len(s) > 10
                        ][:2],
                        # Limit to 2 additional related contexts
                    }
                )

        return info_pairs

    def _generate_qa_pairs(
        self, info_pairs: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Generate multi-hop question-answer pairs"""
        qa_pairs = []

        for pair in info_pairs:
            # 1. Generate multi-hop question-answer pair using AI
            if self.ai_handler:
                # Construct full context
                context = f"{pair['premise']}. {pair['intermediate']}. {pair['conclusion']}"
                ai_qa = self.ai_handler.generate_qa_pair(
                    context=context,
                    related_contexts=pair.get('related_contexts', []),
                )
                if ai_qa:
                    qa_pairs.append(ai_qa)
                    continue

            # 2. If AI generation fails, use a simple template
            # Note: This is a fallback and does not represent true multi-hop QA
            question = f"Based on the following information: {pair['premise']}, what can we conclude about {pair['conclusion']}?"
            answer = f"First, {pair['premise']}. Then, considering that {pair['intermediate']}, we can conclude that {pair['conclusion']}"

            qa_pairs.append(
                {
                    'question': question,
                    'answer': answer,
                    'reasoning_steps': [
                        f"Consider: {pair['premise']}",
                        f"Next, note that: {pair['intermediate']}",
                        f"Finally: {pair['conclusion']}",
                    ],
                    'supporting_facts': [
                        pair['premise'],
                        pair['intermediate'],
                        pair['conclusion'],
                    ],
                    'type': 'template_generated_multi_hop',
                }
            )

        return qa_pairs

    def _calculate_complexity(self, qa_pairs: List[Dict[str, Any]]) -> float:
        """Calculate complexity of QA pairs"""
        if not qa_pairs:
            return 0.0

        # Calculate complexity based on multiple factors
        complexities = []
        for qa in qa_pairs:
            # 1. Number of reasoning steps
            reasoning_steps_count = len(qa.get('reasoning_steps', []))

            # 2. Number of supporting facts
            supporting_facts_count = len(qa.get('supporting_facts', []))

            # 3. Question length
            question_length = len(qa['question'].split())

            # 4. Answer length
            answer_length = len(qa['answer'].split())

            # Calculate complexity of a single QA pair
            qa_complexity = (
                min(reasoning_steps_count / 3, 1.0)
                * 0.4  # Weight for reasoning steps
                + min(supporting_facts_count / 3, 1.0)
                * 0.3  # Weight for supporting facts
                + min(question_length / 20, 1.0)
                * 0.15  # Weight for question length
                + min(answer_length / 50, 1.0) * 0.15
                # Weight for answer length
            )

            complexities.append(qa_complexity)

        return sum(complexities) / len(complexities)


class DataCurator:
    """Data Manager"""

    def __init__(self, config: ProcessorConfig):
        self.config = config

    def curate_dataset(
        self, examples: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Dataset management"""
        logger.info("Starting dataset management...")

        # 1. Quality filtering
        quality_filtered = self._quality_filter(examples)
        logger.info(
            f"Remaining examples after quality filtering: {len(quality_filtered)}"
        )

        # 2. Complexity filtering
        complexity_filtered = self._complexity_filter(quality_filtered)
        logger.info(
            f"Remaining examples after complexity filtering: {len(complexity_filtered)}"
        )

        # 3. Deduplication
        deduplicated = self._remove_duplicates(complexity_filtered)
        logger.info(
            f"Remaining examples after deduplication: {len(deduplicated)}"
        )

        # 4. Sample to target size
        final_dataset = self._sample_dataset(deduplicated)
        logger.info(f"Final dataset size: {len(final_dataset)}")

        return final_dataset

    def _quality_filter(
        self, examples: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Quality filtering"""
        filtered = []

        for example in examples:
            # 1. Check QA pair quality
            qa_quality = self._check_qa_quality(example.get('qa_pairs', []))

            # 2. Check text quality
            text_quality = (
                len(example.get('text', '').split()) >= 20
            )  # At least 20 words

            if qa_quality and text_quality:
                filtered.append(example)

        return filtered

    def _check_qa_quality(self, qa_pairs: List[Dict[str, str]]) -> bool:
        """Check quality of QA pairs"""
        if not qa_pairs:
            return False

        for qa in qa_pairs:
            # 1. Length check
            if (
                len(qa.get('question', '')) < 10
                or len(qa.get('answer', '')) < 5
            ):
                return False

            # 2. QA pair duplication check
            if qa.get('question', '') == qa.get('answer', ''):
                return False

        return True

    def _complexity_filter(
        self, examples: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Complexity filtering"""
        return [
            example
            for example in examples
            if example.get('metadata', {}).get('complexity', 0)
            >= self.config.complexity_threshold
        ]

    def _remove_duplicates(
        self, examples: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicates"""
        seen = set()
        unique_examples = []

        for example in examples:
            # Use text and QA pair combination as unique identifier
            text = example.get('text', '')
            qa_str = str(example.get('qa_pairs', []))

            identifier = hash(text + qa_str)

            if identifier not in seen:
                seen.add(identifier)
                unique_examples.append(example)

        return unique_examples

    def _sample_dataset(
        self, examples: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Sample to target dataset size"""
        if len(examples) <= self.config.dataset_size:
            return examples

        return random.sample(examples, self.config.dataset_size)


def main():
    """Example usage"""
    # Create processor
    config = ProcessorConfig(
        seed=42,
        dataset_size=100,
        quality_threshold=0.7,
        complexity_threshold=0.5,
        use_ai_model=True,
        model_temperature=0.4,
        max_tokens=4096,
    )

    processor = UserDataProcessor(config)

    # Example: Process a single text
    text = """
    Machine learning is a subset of artificial intelligence. It focuses on the development 
    of computer programs that can access data and use it to learn for themselves. 
    The process of learning begins with observations or data, such as examples, direct 
    experience, or instruction. The main aim is to allow the computers learn automatically 
    without human intervention or assistance and adjust actions accordingly.
    """

    result = processor.process_text(text, "example_source")
    logger.info(f"Processing complete! Generated {len(result)} QA pairs")

    # Example: Process multiple texts in batch
    texts = [
        "Text processing is the manipulation of text data. It involves various techniques like tokenization and normalization.",
        "Deep learning is a type of machine learning. It uses artificial neural networks with multiple layers.",
        "Natural language processing combines linguistics and computer science. It helps computers understand human language.",
    ]

    results = processor.process_batch(texts)
    logger.info(
        f"Batch processing complete! Total QA pairs generated: {len(results)}"
    )

    # Print example results
    if results:
        print("\nExample QA pairs:")
        for i, result in enumerate(results[:2], 1):
            print(f"\nExample {i}:")
            for qa in result['qa_pairs'][:2]:
                print(f"Type: {qa['type']}")
                print(f"Question: {qa['question']}")
                print(f"Answer: {qa['answer']}\n")


if __name__ == "__main__":
    main()
