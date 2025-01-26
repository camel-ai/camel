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

import json
import logging

from camel.datagen.source2synth.data_processor import (
    UserDataProcessor,
)
from camel.datagen.source2synth.user_data_processor_config import (
    ProcessorConfig,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def save_results(results, output_file: str):
    r"""Save results to a JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"Results saved to: {output_file}")


def main():
    r"""Example usage."""
    # 1. Create configuration
    config = ProcessorConfig(
        seed=42,
        min_length=50,
        max_length=1000,
        complexity_threshold=0.5,
        dataset_size=10,
        use_ai_model=True,
    )

    # 2. Create the processor
    processor = UserDataProcessor(config)

    # 3. Prepare test data - texts containing multiple related information
    test_texts = [
        # Chain of technological developments
        """
        The invention of transistors revolutionized electronics in the 1950s. 
        These tiny semiconductor devices enabled the development of smaller and more 
        efficient computers. The miniaturization of computers led to the creation of 
        personal computers in the 1980s, which transformed how people work and communicate. 
        This digital revolution eventually gave rise to the internet, connecting billions 
        of people worldwide. Today, this interconnected network powers artificial 
        intelligence systems that are reshaping various industries.
        """,  # noqa: E501
        # Environmental changes causation chain
        """
        Industrial activities have significantly increased carbon dioxide emissions since 
        the Industrial Revolution. These elevated CO2 levels have enhanced the greenhouse 
        effect, trapping more heat in Earth's atmosphere. The rising global temperatures 
        have accelerated the melting of polar ice caps, which has led to rising sea levels. 
        Coastal communities are now facing increased flooding risks, forcing many to 
        consider relocation. This migration pattern is creating new challenges for urban 
        planning and resource management.
        """,  # noqa: E501
        # Biological evolution chain
        """
        The discovery of antibiotics began with Alexander Fleming's observation of 
        penicillin in 1928. The widespread use of these medications has saved countless 
        lives from bacterial infections. However, the extensive use of antibiotics has 
        led to the evolution of resistant bacteria strains. These superbugs now pose 
        a significant challenge to modern medicine, requiring the development of new 
        treatment approaches. Scientists are exploring alternative solutions like 
        bacteriophage therapy to combat antibiotic resistance.
        """,  # noqa: E501
    ]

    # 4. Process a single text
    logger.info("Processing a single text example...")
    single_result = processor.process_text(
        test_texts[0], source="technology_evolution"
    )

    # Save the single text processing result
    save_results(single_result, "single_text_results.json")

    # 5. Batch process texts
    logger.info("Batch processing texts...")
    batch_results = processor.process_batch(
        test_texts,
        sources=["tech_evolution", "climate_change", "medical_evolution"],
    )

    # Save the batch processing results
    save_results(batch_results, "batch_results.json")

    # 6. Print example results
    print("\n=== Single Text Processing Example ===")
    if single_result:
        for i, result in enumerate(single_result, 1):
            print(f"\nText {i}:")
            print(f"Source: {result['metadata']['source']}")
            print(f"Complexity: {result['metadata']['complexity']:.2f}")
            print("\nQ&A Pairs:")
            for j, qa in enumerate(result['qa_pairs'], 1):
                print(f"\nQ&A Pair {j}:")
                print(f"Type: {qa['type']}")
                print(f"Question: {qa['question']}")
                print("Reasoning Steps:")
                for step_num, step in enumerate(
                    qa.get('reasoning_steps', []), 1
                ):
                    print(f"{step_num}. {step}")
                print(f"Answer: {qa['answer']}")
                print("Supporting Facts:")
                for fact_num, fact in enumerate(
                    qa.get('supporting_facts', []), 1
                ):
                    print(f"{fact_num}. {fact}")

    print("\n=== Batch Processing Statistics ===")
    print(f"Total texts processed: {len(test_texts)}")
    pairs_generated = sum(len(result['qa_pairs']) for result in batch_results)
    print(f"Total Q&A pairs generated: {pairs_generated}")

    # 7. Analyze results
    multi_hop_qa = sum(
        1
        for result in batch_results
        for qa in result['qa_pairs']
        if qa['type'] == 'multi_hop_qa'
    )
    template_generated = sum(
        1
        for result in batch_results
        for qa in result['qa_pairs']
        if qa['type'] == 'template_generated_multi_hop'
    )

    print("\n=== Generation Statistics ===")
    print(f"AI-generated multi-hop Q&A count: {multi_hop_qa}")
    print(f"Template-generated multi-hop Q&A count: {template_generated}")

    # 8. Analyze reasoning steps
    avg_steps = sum(
        len(qa.get('reasoning_steps', []))
        for result in batch_results
        for qa in result['qa_pairs']
    ) / sum(len(result['qa_pairs']) for result in batch_results)

    print(f"\nAverage reasoning steps: {avg_steps:.2f}")

    # 9. Calculate average complexity
    avg_complexity = sum(
        result['metadata']['complexity'] for result in batch_results
    ) / len(batch_results)

    print(f"Average complexity score: {avg_complexity:.2f}")


if __name__ == "__main__":
    main()


'''
===============================================================================
Constructing examples: 100%|
███████████████████████████████████████████████████████████████████████████████
█| 1/1 [00:10<00:00, 10.98s/it]
Constructing examples: 100%|
███████████████████████████████████████████████████████████████████████████████
█| 3/3 [00:22<00:00,  7.64s/it]

=== Single Text Processing Example ===

Text 1:
Source: technology_evolution
Complexity: 0.88

Q&A Pairs:

Q&A Pair 1:
Type: multi_hop_qa
Question: How did the invention of transistors impact the development of 
personal computers?
Reasoning Steps:
1. {'step': 'Identify the role of transistors in electronics.'}
2. {'step': 'Understand how transistors enabled the miniaturization of 
computers.'}
3. {'step': 'Connect the miniaturization of computers to the creation of 
personal computers in the 1980s.'}
4. {'step': 'Determine the overall impact of personal computers on work and 
communication.'}
Answer: The invention of transistors allowed for smaller and more efficient 
computers, which led to the development of personal computers in the 1980s, 
transforming work and communication.
Supporting Facts:
1. Transistors are semiconductor devices that revolutionized electronics.
2. The miniaturization of computers was made possible by transistors.
3. Personal computers emerged in the 1980s as a result of smaller computer 
designs.
4. Personal computers changed how people work and communicate.

Q&A Pair 2:
Type: multi_hop_qa
Question: What was the sequence of developments that led from transistors to 
the internet?
Reasoning Steps:
1. {'step': 'Identify how transistors contributed to the development of 
smaller and more efficient computers.'}
2. {'step': 'Explain how the miniaturization of computers resulted in the 
creation of personal computers in the 1980s.'}
3. {'step': 'Discuss how personal computers transformed work and communication.
'}
4. {'step': 'Connect the transformation in communication to the rise of the 
internet.'}
Answer: Transistors enabled smaller computers, which led to personal computers 
in the 1980s, transforming communication and eventually giving rise to the 
internet.
Supporting Facts:
1. Transistors are tiny semiconductor devices that made computers smaller and 
more efficient.
2. The miniaturization of computers allowed for the creation of personal 
computers in the 1980s.
3. Personal computers transformed how people work and communicate.
4. The digital revolution and personal computers contributed to the rise of 
the internet, connecting billions worldwide.

Q&A Pair 3:
Type: multi_hop_qa
Question: How did the miniaturization of computers contribute to the 
development of artificial intelligence systems today?
Reasoning Steps:
1. {'step': 'Identify the impact of miniaturization on the creation of 
personal computers in the 1980s.'}
2. {'step': 'Explain how personal computers transformed communication and work.
'}
3. {'step': 'Connect the digital revolution and the rise of the internet to 
the development of artificial intelligence.'}
4. {'step': 'Discuss how the interconnected network of the internet supports 
AI systems in various industries.'}
Answer: The miniaturization of computers led to personal computers, which 
transformed communication and work, and this digital revolution, along with 
the internet, supports the development of artificial intelligence systems 
today.
Supporting Facts:
1. Miniaturization of computers enabled the creation of personal computers in 
the 1980s.
2. Personal computers transformed how people work and communicate.
3. The digital revolution led to the rise of the internet, connecting billions 
of people.
4. The internet powers artificial intelligence systems that are reshaping 
various industries.

=== Batch Processing Statistics ===
Total texts processed: 3
Total Q&A pairs generated: 9

=== Generation Statistics ===
AI-generated multi-hop Q&A count: 9
Template-generated multi-hop Q&A count: 0

Average reasoning steps: 4.00
Average complexity score: 0.90
===============================================================================
'''
