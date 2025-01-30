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
    3. Generate mapping rules between source and target JSON formats.
    4. Transform the data using the mapping rules.
    5. Save the transformed data to a new JSON file.

    Notes:
        - The input directory is set to "example_data".
        - The target format is loaded from "example_data/target.json".
        - The transformed data is saved to "example_data/output_combined.json".
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
    
    # Generate mapping rules
    mapping_rules = generate_mapping_rules(source_data[0], target_format)
    
    # Transform all data
    transformed_data = [
        transform_data(item, mapping_rules, target_format)
        for item in source_data
    ]
    
    # Save results
    save_json(transformed_data, "output_combined.json")
    print(f"Transformation complete, processed {len(transformed_data)} items")

if __name__ == "__main__":
    example_multiple_files()