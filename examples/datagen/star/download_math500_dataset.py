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

from datasets import load_dataset


def download_huggingface_dataset():
    try:
        # Load the dataset using the datasets library
        dataset = load_dataset("HuggingFaceH4/MATH-500", split="test")

        # Get the first 500 items
        data = dataset.select(range(500))

        # Print the first item to see its structure
        print("Dataset structure:")
        print(data[0])

        # Convert to the desired format
        formatted_data = []
        for _i, item in enumerate(data):
            formatted_item = {
                "id": item['unique_id'],
                "problem": item['problem'],
                "type": item['subject'],  # Include subject as type
                "solution": item['solution'],
                "level": item['level'],
            }
            formatted_data.append(formatted_item)

        # Create output directory if it doesn't exist
        output_dir = Path("examples/datagen/star")
        output_dir.mkdir(exist_ok=True)

        # Save to JSON file
        output_file = output_dir / "math_500_dataset.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(formatted_data, f, indent=4, ensure_ascii=False)

        print(f"Successfully downloaded and saved data to {output_file}")
        return formatted_data

    except Exception as e:
        print(f"Error downloading dataset: {e}")
        return None


if __name__ == "__main__":
    download_huggingface_dataset()
