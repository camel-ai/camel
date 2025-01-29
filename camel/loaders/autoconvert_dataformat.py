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
r"""Module for processing and transforming JSON/JSONL data files.

This module provides functions to load, transform, and save JSON/JSONL data
files. It supports generating mapping rules between source and target JSON
formats, and applying these rules to transform data accordingly. The module
also includes utilities for cleaning JSON responses and handling nested
structures.

Functions:
    load_json: Load data from a single JSON or JSONL file.
    load_multiple_json: Load data from multiple JSON or JSONL files.
    get_all_keys: Recursively extract all keys from nested JSON structures.
    clean_json_response: Clean markdown formatting from AI-generated JSON.
    generate_mapping_rules: Generate mapping rules between source and target JSON.
    transform_data: Transform source data using mapping rules.
    save_json: Save data to a JSON file.
    main: Main function to process JSON/JSONL files for data transformation.
"""

import json
import os
from camel.agents import ChatAgent

from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
import argparse


model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig(temperature=0.2).as_dict(),
)
# Define the system message
sys_msg = "You are a helpful assistant."

# Initialize ChatAgent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

def load_json(file_path, n=None):
    r"""Read data from a JSON or JSONL file.

    Args:
        file_path (str): Path to the JSON or JSONL file.
        n (int, optional): If specified, only read the first n lines. If None,
            read all lines. Defaults to None.

    Returns:
        list: A list of JSON objects loaded from the file.

    Raises:
        FileNotFoundError: If no valid JSON or JSONL file is found.
    """
    # Check if the file exists
    if not os.path.exists(file_path):
        # Try different extensions
        base_path = os.path.splitext(file_path)[0]
        for ext in ['.json', '.jsonl']:
            alt_path = base_path + ext
            if os.path.exists(alt_path):
                file_path = alt_path
                break
        else:
            raise FileNotFoundError(f"No JSON or JSONL file found for {file_path}")

    with open(file_path, 'r') as file:
        # Check the file extension
        if file_path.endswith('.jsonl'):
            # JSONL format: each line is a JSON object
            data = []
            for i, line in enumerate(file):
                if n is not None and i >= n:
                    break
                data.append(json.loads(line.strip()))
            return data
        else:
            # Regular JSON format
            data = json.load(file)
            if isinstance(data, list):
                return data[:n] if n is not None else data
            else:
                return [data]

def load_multiple_json(file_paths, n=None):
    r"""Read data from multiple JSON or JSONL files.

    Args:
        file_paths (Union[str, List[str]]): List of file paths or a single file
            path.
        n (int, optional): If specified, only read the first n lines from each
            file. If None, read all lines. Defaults to None.

    Returns:
        list: A list of JSON objects loaded from all files.
    """
    if isinstance(file_paths, str):
        file_paths = [file_paths]
    
    all_data = []
    for file_path in file_paths:
        try:
            data = load_json(file_path, n)
            all_data.extend(data if isinstance(data, list) else [data])
        except Exception as e:
            print(f"Error processing file {file_path}: {str(e)}")
            continue
    
    return all_data

def get_all_keys(data, prefix=''):
    r"""Recursively get all keys from a nested JSON structure.

    Args:
        data (Union[dict, list]): The JSON data to extract keys from.
        prefix (str, optional): Prefix for nested keys. Defaults to ''.

    Returns:
        set: A set of all keys in the JSON structure.
    """
    keys = set()
    if isinstance(data, dict):
        for key, value in data.items():
            current_key = f"{prefix}{key}" if prefix else key
            keys.add(current_key)
            keys.update(get_all_keys(value, f"{current_key}."))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            keys.update(get_all_keys(item, f"{prefix}[{i}]."))
    return keys

def clean_json_response(response):
    r"""Clean markdown formatting from AI-generated JSON content.

    Args:
        response (str): The AI-generated response containing JSON.

    Returns:
        str: The cleaned JSON content without markdown formatting.
    """
    content = response.strip()
    
    # Remove markdown code block markers
    if content.startswith('```'):
        # Find the positions of the first and last ```
        first = content.find('\n')
        last = content.rfind('```')
        if first != -1 and last != -1:
            content = content[first:last].strip()
    
    return content

def generate_mapping_rules(source_data, target_data):
    r"""Generate mapping rules between source and target JSON structures.

    Args:
        source_data (dict): Source JSON data.
        target_data (dict): Target JSON data.

    Returns:
        dict: A dictionary mapping source keys to target keys.

    Raises:
        ValueError: If the mapping contains invalid target keys.
        json.JSONDecodeError: If the AI response is not valid JSON.
    """
    # Get all keys from source and target data
    source_keys = get_all_keys(source_data)
    target_keys = get_all_keys(target_data)
    
    # Build the prompt
    prompt = f"""
    Here are two JSON data samples:

    Source JSON:
    {json.dumps(source_data, indent=5)}

    Target JSON:
    {json.dumps(target_data, indent=5)}

    Target JSON has the following keys: {sorted(list(target_keys))}

    Please analyze the keys in the source JSON and target JSON, and generate a mapping rule.
    IMPORTANT: 
    1. Your response must be ONLY a valid JSON object.
    2. Only map to keys that exist in the target JSON structure.
    3. The mapping should be from source keys to target keys.
    4. Do not include any keys that don't exist in the target structure.
    5. Do not use markdown formatting or code blocks in your response.

    Example format:
    {{
        "source_key_1": "target_key_1",
        "source_key_2": "target_key_2"
    }}
    """
    try:
        response = camel_agent.step(prompt)
        # Clean the response content
        cleaned_content = clean_json_response(response.msgs[0].content)
        mapping = json.loads(cleaned_content)
        
        # Verify that the mapping rules only contain keys existing in the target format
        invalid_target_keys = set(mapping.values()) - target_keys
        if invalid_target_keys:
            raise ValueError(f"Mapping contains invalid target keys: {invalid_target_keys}")
            
        return mapping
    except json.JSONDecodeError as e:
        print(f"Error: AI response was not valid JSON. Response content: {response.msgs[0].content}")
        print(f"Cleaned content was: {cleaned_content}")
        raise
    except Exception as e:
        print(f"Error generating mapping rules: {str(e)}")
        raise

def transform_data(source_data, mapping_rules, target_structure):
    r"""Transform source data using mapping rules.

    Args:
        source_data (dict): Source JSON data.
        mapping_rules (dict): Mapping rules from source to target keys.
        target_structure (dict): Target JSON structure for reference.

    Returns:
        dict: Transformed JSON data matching the target structure.
    """
    transformed_data = {}
    
    # Only transform fields specified in the mapping rules
    for source_key, target_key in mapping_rules.items():
        if source_key in source_data:
            # Handle nested keys
            keys = target_key.split('.')
            current_dict = transformed_data
            for i, key in enumerate(keys[:-1]):
                current_dict = current_dict.setdefault(key, {})
            current_dict[keys[-1]] = source_data[source_key]
    
    return transformed_data

def save_json(data, file_path):
    r"""Save JSON data to a file.

    Args:
        data (Union[dict, list]): JSON data to save.
        file_path (str): Path to the output JSON file.
    """
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def main():
    r"""Main function to process JSON/JSONL files for data transformation.

    This function handles command-line arguments, loads source and target data,
    generates mapping rules, transforms the data, and saves the output.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Process JSON/JSONL files for data transformation')
    parser.add_argument('input_files', nargs='+', help='Input JSON/JSONL file(s)')
    parser.add_argument('--target', required=True, help='Target JSON file for format reference')
    parser.add_argument('--output', required=True, help='Output JSON file')
    parser.add_argument('-n', type=int, help='Number of lines to process from each input file')
    args = parser.parse_args()

    # Load source data from multiple files
    source_data = load_multiple_json(args.input_files, args.n)
    if not source_data:
        print("No valid data found in input files")
        return

    # Load target format
    target_data = load_json(args.target)[0]  # Use first item as reference

    # Generate mapping rules
    mapping_rules = generate_mapping_rules(source_data[0], target_data)
    
    # Transform all data
    transformed_data = []
    for item in source_data:
        try:
            transformed = transform_data(item, mapping_rules, target_data)
            transformed_data.append(transformed)
        except Exception as e:
            print(f"Error transforming item: {str(e)}")
            continue

    # Save transformed data
    save_json(transformed_data, args.output)
    print(f"Processed {len(transformed_data)} items from {len(args.input_files)} files")
    print(f"Output saved to: {args.output}")

if __name__ == "__main__":
    main()