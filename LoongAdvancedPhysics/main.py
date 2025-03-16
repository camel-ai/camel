from pipeline import PhysicsCodeGenPipeline
from camel.models import DeepSeekModel, OpenAIModel
from camel.types import ModelType
from typing import Dict, Literal
import os
import json
import logging
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--dataset", type=str, required=True, help="Which dataset to use: OlympiadBench or SciBench")
parser.add_argument("--num", type=int, required=False, help="Number of samples to generate. If not provided, all samples will be generated.")
parser.add_argument("--out_location", type=str, required=False, help="Output directory for the generated samples.")
args = parser.parse_args()

def preprocess_data(data: Dict, dataset_origin: Literal["OlympiadBench", "SciBench"]):

    if dataset_origin == "OlympiadBench":
        # Create a new dictionary with the selected keys.
        processed = {
            "id": data.get("id"),
            "question": data.get("context") + '\n' + data.get("question"),
            "gt_answer": data.get("final_answer")[0],
            "unit": data.get("unit"),
            "metadata": {}
        }
        
        # Define keys that should be moved out of metadata.
        keys_to_exclude = {"id", "question", "context", "final_answer"}
    elif dataset_origin == "SciBench":
        processed = {
            "id": data.get("problem_id"),
            "question": data.get("problem_text"),
            "gt_answer": data.get("answer_number"),
            "unit": data.get("unit"),
            "metadata": {}
        }
        
        keys_to_exclude = {"problem_id", "problem_text", "answer_number"}
    
    # Put the remaining keys into metadata.
    for key, value in data.items():
        if key not in keys_to_exclude:
            processed["metadata"][key] = value
            
    return processed

def preprocess_dataset(dataset_origin: Literal["OlympiadBench", "SciBench"]):

    if dataset_origin == "OlympiadBench":
        dataset_path = os.path.join(current_path, "PhysicsDatasets/OlympiadBench/")
        files = ['OE_TO_physics_en_COMP.json']
    elif dataset_origin == "SciBench":
        dataset_path = os.path.join(current_path, "PhysicsDatasets/SciBench/")
        files = ['class_sol.json', 'fund_sol.json', 'thermo_sol.json']
    else:
        raise ValueError("Invalid dataset name. Please choose either 'OlympiadBench' or 'SciBench'.")

    dataset = []
    for file in files:
        with open(os.path.join(dataset_path, file)) as f:
            d = json.load(f)
            f.close()
        dataset += d

    processed_dataset = []
    for data in dataset:
        processed_data = preprocess_data(data, dataset_origin)
        processed_dataset.append(processed_data)

    return processed_dataset

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    current_path = os.path.dirname(os.path.abspath(__file__))

    dataset = preprocess_dataset(args.dataset)

    reason_model = OpenAIModel(
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict={
            "temperature": 0.2,
        }
    )
    
    output_location = args.out_location if args.out_location else os.path.join(current_path, "output.json")

    pipeline = PhysicsCodeGenPipeline(
        reason_model=reason_model,
        dataset=dataset,
        num=args.num,
        output_location = output_location
    )

    pipeline.run()