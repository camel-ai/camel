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
import os
from typing import Dict, List

from camel.datasets.medicine import MedicineDataset


def load_medical_cases() -> List[Dict]:
    """
    Load medical cases from the JSON file.

    Returns:
        List[Dict]: List of medical cases with their associated information
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "medical_cases.json")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data["cases"]


def display_case(case: Dict) -> None:
    """
    Display a medical case in a formatted way.

    Args:
        case (Dict): A medical case containing detailed information
    """
    print("Case ID:", case["id"])
    print("-" * 80)

    print("\nDescription:")
    print(case["description"])

    print("\nSolution:")
    print(case["solution"])

    print("\nVerified Solution:")
    print(case["verified_solution"])

    print("\nClinical Reasoning:")
    print(case["clinical_reasoning"])

    print("\nMetadata:")
    print(f"Complexity: {case['complexity']}")
    print(f"Category: {case['category']}")
    print(f"Specialty: {case['medical_speciality']}")
    print(f"Evidence Level: {case['evidence_level']}")
    print(f"ICD Codes: {', '.join(case['icd_codes'])}")


def demonstrate_dataset_usage():
    """
    Demonstrate how to use the MedicineDataset class.
    """
    print("\nDemonstrating MedicineDataset Usage:")
    print("=" * 80)

    # Initialize the dataset
    dataset = MedicineDataset(
        categories=["diagnosis", "pulmonology", "rheumatology"],
        difficulty_levels=["basic", "intermediate", "advanced"],
    )

    # Note: In a real implementation, you would await dataset.setup()
    print("\nDataset Metadata:")
    print(f"Domain: {dataset._metadata['domain']}")
    print(f"Categories: {dataset._metadata['categories']}")
    print(f"Difficulty Levels: {dataset._metadata['difficulty_levels']}")


def main():
    # Load and display the medical cases
    cases = load_medical_cases()

    for i, case in enumerate(cases, 1):
        print(f"\nCase {i}:")
        print("=" * 80)
        display_case(case)
        print("\n")

    # Demonstrate dataset class usage
    demonstrate_dataset_usage()


if __name__ == "__main__":
    main()
