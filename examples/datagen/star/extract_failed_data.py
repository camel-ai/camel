import json
import os

FILEPATH = os.path.dirname(__file__)
RESULT_PATH = os.path.join(FILEPATH, "outputs/gsm8k_dataset_output_part1.json")
ORIGINAL_DATASET_PATH = os.path.join(FILEPATH, "gsm8k_dataset_part1.json")
EXTRACTED_DATASET_PATH = os.path.join(
    FILEPATH, "outputs/gsm8k_dataset_part1_failed.json"
)


if __name__ == "__main__":
    with open(RESULT_PATH, "r") as f:
        results = json.load(f)["traces"]
    failed_ids = {
        result["id"]
        for result in results
        if not result["boxed_answer_success"]
    }

    with open(ORIGINAL_DATASET_PATH, "r") as f:
        original_dataset = json.load(f)

    extracted_dataset = [
        data for data in original_dataset if data["id"] in failed_ids
    ]

    with open(EXTRACTED_DATASET_PATH, "w") as f:
        json.dump(extracted_dataset, f, indent=2)
