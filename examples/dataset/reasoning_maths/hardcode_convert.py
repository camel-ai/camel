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
import glob
import json
from camel.loaders import (
    load_json,
    load_multiple_json,
    generate_mapping_rules,
    transform_data,
    save_json
)

def load_jsonl(file_path):
    """Load data from a JSONL file.

    Args:
        file_path (str): Path to the JSONL file.

    Returns:
        list: List of JSON objects from the file.
    """
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():  # Skip empty lines
                data.append(json.loads(line))
    return data

def get_json_files(directory):
    r"""Retrieve all .json and .jsonl files in a directory.

    Args:
        directory (str): Path to the directory containing JSON/JSONL files.

    Returns:
        list: A list of file paths for all .json and .jsonl files in the directory.
    """
    json_files = glob.glob(os.path.join(directory, "*.json"))
    jsonl_files = glob.glob(os.path.join(directory, "*.jsonl"))
    return json_files + jsonl_files

def example_multiple_files():
    r"""Example function to process multiple JSON/JSONL files.

    This function demonstrates how to:
    1. Retrieve all JSON/JSONL files from a directory.
    2. Load and combine data from multiple files.
    3. Transform the data to match the target format.
    4. Save the transformed data to a new JSON file.
    """
    print("\n=== Example 2: Process multiple JSON and JSONL files ===")
    
    # Retrieve all .json and .jsonl files in the directory
    input_directory = "downloadeddata_files"
    input_files = get_json_files(input_directory)
    
    if not input_files:
        print(f"No JSON or JSONL files found in directory: {input_directory}")
        return
    
    # Load multiple source files
    source_data = []
    for file_path in input_files:
        try:
            # Try loading as JSONL first
            data = load_jsonl(file_path)
            if data:
                source_data.extend(data)
            else:
                # If no data was loaded, try regular JSON
                data = load_json(file_path)
                source_data.extend(data if isinstance(data, list) else [data])
        except Exception as e:
            print(f"Error processing file {file_path}: {str(e)}")
    
    if not source_data:
        print("No valid data could be loaded from the files")
        return
        
    target_format = load_json("target.json")[0]
    
    # Transform all data
    transformed_data = []
    for i, item in enumerate(source_data):
        # Get the problem text, prioritize the "problem" field, if not exist, use the "question" field
        problem_text = item.get("problem", item.get("question", ""))
        
        # Determine the problem type
        problem_type = "algebra"  # Default type
        if "data_topic" in item:
            topic = item["data_topic"].lower()
            if "algebra" in topic:
                problem_type = "algebra"
            elif "combinatorics" in topic:
                problem_type = "combinatorics"
            elif "proof" in topic:
                problem_type = "mathematical_proof"
            
        transformed = {
            "id": f"problem_{i}",
            "problem": problem_text,
            "type": problem_type,
            "solution": str(item.get("answer", ""))
        }
        transformed_data.append(transformed)
    
    # Save results
    save_json(transformed_data, "output_combined.json")
    print(f"Transformation complete, processed {len(transformed_data)} items")

if __name__ == "__main__":
    example_multiple_files()