import json
from datetime import datetime

def transform_qa_format(input_file):
    # Read the input JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Transform the data
    transformed_data = []
    for question, answer in data['qa_pairs'].items():
        transformed_pair = {
            "instruction": question,
            "input": "",
            "output": answer
        }
        transformed_data.append(transformed_pair)
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'transformed_qa_{timestamp}.json'
    
    # Write the transformed data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(transformed_data, f, ensure_ascii=False, indent=2)
    
    return output_file

if __name__ == "__main__":
    # Use the latest generated answers file
    input_file = "generated_answers_20241210_104117.json"
    output_file = transform_qa_format(input_file)
    print(f"Transformation complete. Output saved to: {output_file}")
