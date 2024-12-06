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

from camel.synthetic_datagen.source2synth.data_processor import (
    UserDataProcessor,
)
from camel.synthetic_datagen.source2synth.user_data_processor_config import (
    ProcessorConfig,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def save_results(results, output_file: str):
    """Save results to a JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"Results saved to: {output_file}")


def main():
    """Example usage."""
    # 1. Create configuration
    config = ProcessorConfig(
        seed=42,
        min_length=50,
        max_length=1000,
        quality_threshold=0.7,
        complexity_threshold=0.5,
        dataset_size=10,
        use_ai_model=True,
    )

    # 2. Create the processor
    processor = UserDataProcessor(config)

    # 3. Prepare test data - texts containing multiple related pieces of information
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
        """,
        # Environmental changes causation chain
        """
        Industrial activities have significantly increased carbon dioxide emissions since 
        the Industrial Revolution. These elevated CO2 levels have enhanced the greenhouse 
        effect, trapping more heat in Earth's atmosphere. The rising global temperatures 
        have accelerated the melting of polar ice caps, which has led to rising sea levels. 
        Coastal communities are now facing increased flooding risks, forcing many to 
        consider relocation. This migration pattern is creating new challenges for urban 
        planning and resource management.
        """,
        # Biological evolution chain
        """
        The discovery of antibiotics began with Alexander Fleming's observation of 
        penicillin in 1928. The widespread use of these medications has saved countless 
        lives from bacterial infections. However, the extensive use of antibiotics has 
        led to the evolution of resistant bacteria strains. These superbugs now pose 
        a significant challenge to modern medicine, requiring the development of new 
        treatment approaches. Scientists are exploring alternative solutions like 
        bacteriophage therapy to combat antibiotic resistance.
        """,
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
    print(
        f"Total Q&A pairs generated: {sum(len(result['qa_pairs']) for result in batch_results)}"
    )

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
