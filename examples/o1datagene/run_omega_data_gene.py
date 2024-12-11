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

import os
import json
from datetime import datetime
from getpass import getpass
from dotenv import load_dotenv

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import ChatGPTConfig
from camel.agents import ChatAgent

from omega_data_gene import OmegaDataGene, logger

def load_qa_data(file_path):
    """Load Q&A data from a JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading QA data: {str(e)}")
        return {}

def main():
    # Set up OpenAI API key
    openai_api_key = getpass('Enter your OpenAI API key: ')
    os.environ["OPENAI_API_KEY"] = openai_api_key
    load_dotenv()

    # System message for the agent
    sys_msg = 'You are a genius at slow-thinking data and code generation, specializing in step-by-step reasoning.'

    # Initialize the model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=ChatGPTConfig(
            temperature=0.7,  # Slightly higher for more diverse reasoning
            max_tokens=4096
        ).as_dict(),
    )

    # Initialize chat agent
    chat_agent = ChatAgent(
        system_message=sys_msg,
        model=model,
        message_window_size=10,
    )

    # Load QA data
    qa_data = load_qa_data('qa_data.json')
    if not qa_data:
        logger.error("Failed to load QA data. Exiting.")
        return

    # Initialize OmegaDataGene with optimized parameters
    omega_gene = OmegaDataGene(
        chat_agent=chat_agent,
        golden_answers=qa_data,
        c_puct=0.5,      # Exploration-exploitation balance
        alpha=0.5,       # MC(s) weight
        beta=0.9,        # Length penalty
        max_steps=20,    # Maximum search steps
        num_rollouts=16, # Number of Monte Carlo rollouts
        rollout_budget=200  # Total rollout budget
    )

    # Process questions and generate answers
    generated_answers = {}
    total_questions = len(qa_data)
    
    logger.info(f"Starting to process {total_questions} questions")
    
    for idx, question in enumerate(qa_data.keys(), 1):
        logger.info(f"\nProcessing question {idx}/{total_questions}: {question}")
        
        try:
            # Generate solution using improved algorithm
            solution = omega_gene.solve(question)
            generated_answers[question] = solution
            
            # Log progress
            logger.info(f"Solution generated for question {idx}")
            logger.info("-" * 50)
            
        except Exception as e:
            logger.error(f"Error processing question {idx}: {str(e)}")
            continue

    # Export results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Export detailed solutions with search tree information
    omega_gene.export_solutions(f'omega_solutions_{timestamp}.json')
    
    # Export simplified version with just Q&A pairs
    simplified_output = {
        'timestamp': datetime.now().isoformat(),
        'qa_pairs': generated_answers,
        'total_questions': total_questions,
        'successful_generations': len(generated_answers)
    }
    
    simplified_file = f'generated_answers_{timestamp}.json'
    with open(simplified_file, 'w', encoding='utf-8') as f:
        json.dump(simplified_output, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Results exported to:")
    logger.info(f"1. Detailed solutions: omega_solutions_{timestamp}.json")
    logger.info(f"2. Simplified Q&A pairs: {simplified_file}")
    logger.info(f"Successfully processed {len(generated_answers)}/{total_questions} questions")

if __name__ == "__main__":
    main()
