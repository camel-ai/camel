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

import requests
from datasets import load_dataset


def download_math500_dataset():
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
                "type": "HuggingFaceH4/MATH-500\n"
                + item['subject'],  # Include subject as type
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


def download_aime24_dataset():
    try:
        # Direct API endpoint for the dataset
        url = "https://datasets-server.huggingface.co/rows?dataset=HuggingFaceH4%2Faime_2024&config=default&split=train&offset=0&length=100"
        response = requests.get(url)

        if not response.ok:
            raise Exception(f"Failed to fetch data: {response.status_code}")

        data = response.json()

        # Convert to the desired format
        formatted_data = []
        for row in data.get('rows', []):
            item = row.get('row', {})
            formatted_item = {
                "id": item.get('id', ''),
                "problem": item.get('problem', ''),
                "type": "HuggingFaceH4/aime_2024",
                "solution": item.get('solution', ''),
                "answer": item.get('answer', None),
                "url": item.get('url', ''),
                "year": item.get('year', ''),
            }
            formatted_data.append(formatted_item)

        # Create output directory if it doesn't exist
        output_dir = Path("examples/datagen/star")
        output_dir.mkdir(exist_ok=True)

        # Save to JSON file
        output_file = output_dir / "aime24_dataset.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(formatted_data, f, indent=4, ensure_ascii=False)

        print(
            f"Successfully downloaded and saved AIME24 data to {output_file}"
        )
        return formatted_data

    except Exception as e:
        print(f"Error downloading AIME24 dataset: {e}")
        return None


def download_amc23_dataset():
    try:
        # Direct API endpoint for the dataset
        url = "https://datasets-server.huggingface.co/rows?dataset=zwhe99%2Famc23&config=default&split=test&offset=0&length=100"
        response = requests.get(url)

        if not response.ok:
            raise Exception(f"Failed to fetch data: {response.status_code}")

        data = response.json()

        # Convert to the desired format
        formatted_data = []
        for row in data.get('rows', []):
            item = row.get('row', {})
            formatted_item = {
                "id": item.get('id', ''),
                "problem": item.get('question', ''),
                "type": "zwhe99/amc23",  # All problems are from AMC23
                "solution": f"\\boxed{{{item.get('answer', '').strip('$')}}}",
                "answer": item.get('answer', None),
            }
            formatted_data.append(formatted_item)

        # Create output directory if it doesn't exist
        output_dir = Path("examples/datagen/star")
        output_dir.mkdir(exist_ok=True)

        # Save to JSON file
        output_file = output_dir / "amc23_dataset.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(formatted_data, f, indent=4, ensure_ascii=False)

        print(f"Successfully downloaded and saved AMC23 data to {output_file}")
        return formatted_data

    except Exception as e:
        print(f"Error downloading AMC23 dataset: {e}")
        return None


def download_gaokao2023_dataset():
    try:
        # Direct API endpoint for the dataset
        url = "https://datasets-server.huggingface.co/rows?dataset=MARIO-Math-Reasoning%2FGaokao2023-Math-En&config=default&split=train&offset=0&length=100"
        response = requests.get(url)

        if not response.ok:
            raise Exception(f"Failed to fetch data: {response.status_code}")

        data = response.json()

        # Convert to the desired format
        formatted_data = []
        for row in data.get('rows', []):
            item = row.get('row', {})
            formatted_item = {
                "id": item.get('id', ''),
                "problem": item.get('question', ''),
                "type": "MARIO-Math-Reasoning/Gaokao2023",
                "solution": f"\\boxed{{{item.get('answer', '').strip('$')}}}",
                "answer": item.get('answer', None),
            }
            formatted_data.append(formatted_item)

        # Create output directory if it doesn't exist
        output_dir = Path("examples/datagen/star")
        output_dir.mkdir(exist_ok=True)

        # Save to JSON file
        output_file = output_dir / "gaokao2023_dataset.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(formatted_data, f, indent=4, ensure_ascii=False)

        print(
            f"Successfully downloaded and saved Gaokao2023 data "
            f"to {output_file}"
        )
        return formatted_data

    except Exception as e:
        print(f"Error downloading Gaokao2023 dataset: {e}")
        return None


def download_gsm8k_dataset():
    try:
        # Direct API endpoint for the dataset
        url = "https://datasets-server.huggingface.co/rows?dataset=openai%2Fgsm8k&config=main&split=train&offset=0&length=100"
        response = requests.get(url)

        if not response.ok:
            raise Exception(f"Failed to fetch data: {response.status_code}")

        data = response.json()

        # Convert to the desired format
        formatted_data = []
        for row in data.get('rows', []):
            item = row.get('row', {})
            # Extract the final answer from the solution
            solution = item.get('answer', '')
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
                "id": None,  # GSM8K doesn't provide IDs
                "problem": item.get('question', ''),
                "type": "openai/gsm8k",  # All problems are from GSM8K
                "solution": solution,  # Use the modified solution with \boxed
            }
            formatted_data.append(formatted_item)

        # Create output directory if it doesn't exist
        output_dir = Path("examples/datagen/star")
        output_dir.mkdir(exist_ok=True)

        # Save to JSON file
        output_file = output_dir / "gsm8k_dataset.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(formatted_data, f, indent=4, ensure_ascii=False)

        print(f"Successfully downloaded and saved GSM8K data to {output_file}")
        return formatted_data

    except Exception as e:
        print(f"Error downloading GSM8K dataset: {e}")
        return None


def download_openthoughts_dataset():
    try:
        # Direct API endpoint for the dataset
        # Get only top 100 records by setting length=100 in the URL
        url = (
            "https://datasets-server.huggingface.co/rows?"
            "dataset=open-r1%2FOpenThoughts-114k-math&config=default"
            "&split=train&offset=0&length=100"
        )
        response = requests.get(url)

        if not response.ok:
            raise Exception(f"Failed to fetch data: {response.status_code}")

        data = response.json()
        rows = data.get('rows', [])[:100]  # Ensure we only take top 100 records

        # Convert to the desired format
        formatted_data = []
        for row in rows:
            item = row.get('row', {})
            formatted_item = {
                "id": item.get('id', ''),
                "problem": item.get('problem', ''),
                "type": "open-r1/OpenThoughts-114k-math\n" + item.get('source', ''),
                "solution": item.get('solution', ''),
            }
            formatted_data.append(formatted_item)

        # Create output directory if it doesn't exist
        output_dir = Path("examples/datagen/star")
        output_dir.mkdir(exist_ok=True)

        # Save to JSON file
        output_file = output_dir / "openthoughts_math.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(formatted_data, f, indent=4, ensure_ascii=False)

        print(
            f"Successfully downloaded and saved OpenThoughts data "
            f"to {output_file}"
        )
        return formatted_data

    except Exception as e:
        print(f"Error downloading OpenThoughts dataset: {e}")
        return None


if __name__ == "__main__":
    # download_math500_dataset()
    # download_aime24_dataset()
    # download_amc23_dataset()
    # download_gaokao2023_dataset()
    # download_gsm8k_dataset()
    download_openthoughts_dataset()
