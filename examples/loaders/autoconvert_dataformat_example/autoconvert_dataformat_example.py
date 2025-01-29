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

"""
Example: How to use the conversion functions in test.py as a module

This example demonstrates how to call conversion functions directly in the code:
1. Process a single JSON file
2. Process multiple JSON/JSONL files
3. Customize the conversion process
"""

from camel.loaders import (
    load_json,
    load_multiple_json,
    generate_mapping_rules,
    transform_data,
    save_json
)

def example_single_file():
    r"""Example 1: Process a single JSON file"""
    print("\n=== Example 1: Process a single JSON file ===")
    
    # Load source data and target format
    source_data = load_json("example_data/input1.json")
    target_format = load_json("example_data/target.json")[0]
    
    # Generate mapping rules
    mapping_rules = generate_mapping_rules(source_data[0], target_format)
    print("Generated mapping rules:", mapping_rules)
    
    # Transform data
    transformed_data = [
        transform_data(item, mapping_rules, target_format)
        for item in source_data
    ]
    
    # Save results
    save_json(transformed_data, "example_data/output1.json")
    print("Transformation complete, results saved to output1.json")

def example_multiple_files():
    r"""Example 2: Process multiple files"""
    print("\n=== Example 2: Process multiple JSON and JSONL files ===")
    
    # Load multiple source files
    input_files = [
        "example_data/input1.json",
        "example_data/input2.jsonl"
    ]
    source_data = load_multiple_json(input_files)
    target_format = load_json("example_data/target.json")[0]
    
    # Generate mapping rules
    mapping_rules = generate_mapping_rules(source_data[0], target_format)
    
    # Transform all data
    transformed_data = [
        transform_data(item, mapping_rules, target_format)
        for item in source_data
    ]
    
    # Save results
    save_json(transformed_data, "example_data/output_combined.json")
    print(f"Transformation complete, processed {len(transformed_data)} items")

def example_custom_processing():
    r"""Example 3: Custom transformation process"""
    print("\n=== Example 3: Custom transformation process ===")
    
    # Load data
    source_data = load_multiple_json("example_data/input1.json", n=2)  # Only process the first 2 items
    target_format = load_json("example_data/target.json")[0]
    
    # Generate mapping rules
    mapping_rules = generate_mapping_rules(source_data[0], target_format)
    
    # Custom transformation process
    transformed_data = []
    for item in source_data:
        # Custom processing logic can be added before and after transformation
        transformed = transform_data(item, mapping_rules, target_format)
        # For example: add an additional field
        transformed["processed_at"] = "2025-01-29"
        transformed_data.append(transformed)
    
    # Save results
    save_json(transformed_data, "example_data/output_custom.json")
    print("Custom transformation complete")

if __name__ == "__main__":
    # Run all examples
    example_single_file()
    example_multiple_files()
    example_custom_processing()
