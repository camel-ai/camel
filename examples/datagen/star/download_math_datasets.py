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
from pathlib import Path
import uuid

from datasets import load_dataset

def download_gsm8k_dataset():
    try:
        # Load the dataset using the datasets library
        dataset = load_dataset("openai/gsm8k", "main")

        # Get the first 7473 items from train split
        data = dataset['train'].select(range(7473))

        # Convert to the desired format
        formatted_data = []
        for item in data:
            # Extract the final answer from the solution
            solution = item['answer']
            if solution:
                # GSM8K solutions typically end with "#### number"
                import re

                match = re.search(r'####\s*(\d+)', solution)
                if match:
                    number = match.group(1)
                    # Replace the "#### number" with "\boxed{number}"
                    solution = re.sub(
                        r'####\s*\d+', f'\\\\boxed{{{number}}}', solution
                    )

            formatted_item = {
                "id": str(uuid.uuid4()),  # GSM8K doesn't provide IDs
                "problem": item['question'],
                "type": "openai/gsm8k",  # All problems are from GSM8K
                "solution": solution,  # Use the modified solution with \boxed
            }
            formatted_data.append(formatted_item)

        # Create output directory if it doesn't exist
        output_dir = Path("examples/datagen/star")
        output_dir.mkdir(exist_ok=True)

        # Split data into 4 parts, each containing less than 2000 records
        total_records = len(formatted_data)
        base_size = total_records // 4
        remainder = total_records % 4
        
        datasets = []
        start = 0
        for i in range(4):
            # Add one extra item to some chunks to distribute remainder
            chunk_size = base_size + (1 if i < remainder else 0)
            end = start + chunk_size
            datasets.append(formatted_data[start:end])
            start = end

        # Save each part to a separate JSON file
        for i, dataset_part in enumerate(datasets, 1):
            output_file = output_dir / f"gsm8k_dataset_part{i}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(dataset_part, f, indent=4, ensure_ascii=False)
            print(f"Successfully saved part {i} ({len(dataset_part)} records) to {output_file}")

        return formatted_data

    except Exception as e:
        print(f"Error downloading GSM8K dataset: {e}")
        return None

def download_amc_aime_dataset():
    try:
        # Load the dataset using the datasets library
        dataset = load_dataset("mlfoundations-dev/bespokelabs-sky-t1-numina-amc-aime-subset-unfiltered")

        # Get the first 4070 items from train split
        data = dataset['train'].select(range(4069))

        # Convert to the desired format
        formatted_data = []
        for item in data:
            formatted_item = {
                "id": str(uuid.uuid4()),
                "problem": item['problem'],
                "type": "amc_aime",
                "solution": item['ground_truth_solution']
            }
            formatted_data.append(formatted_item)

        # Create output directory if it doesn't exist
        output_dir = Path("examples/datagen/star")
        output_dir.mkdir(exist_ok=True)

        # Split data into 4 parts, each containing less than 2000 records
        total_records = len(formatted_data)
        base_size = total_records // 4
        remainder = total_records % 4
        
        datasets = []
        start = 0
        for i in range(4):
            # Add one extra item to some chunks to distribute remainder
            chunk_size = base_size + (1 if i < remainder else 0)
            end = start + chunk_size
            datasets.append(formatted_data[start:end])
            start = end

        # Save each part to a separate JSON file
        for i, dataset_part in enumerate(datasets, 1):
            output_file = output_dir / f"amc_aime_dataset_part{i}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(dataset_part, f, indent=4, ensure_ascii=False)
            print(f"Successfully saved part {i} ({len(dataset_part)} records) to {output_file}")

        return formatted_data

    except Exception as e:
        print(f"Error downloading AMC/AIME dataset: {e}")
        return None




if __name__ == "__main__":
    # download_gsm8k_dataset()
    download_amc_aime_dataset()
