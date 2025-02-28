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
import asyncio
from datetime import datetime
from typing import Dict, Any

from pydantic import ConfigDict
from camel.verifiers.medicine import MedicalVerifier
from camel.verifiers.models import (
    Response,
    TaskType,
    BaseConfig,
    MachineInfo,
    ModelType,
)



class CustomResponse(Response):
    model_config = ConfigDict(protected_namespaces=())


def create_test_response(
    medical_content: Dict[str, Any],
    problem_id: str = "test_case",
) -> Response:
    """Create a test medical response.

    Args:
        medical_content: Medical content for verification
        problem_id: Unique identifier for the test case

    Returns:
        Response: Test medical response object
    """
    return CustomResponse(  
        problem_id=problem_id,
        source="test",
        task_type=TaskType.MEDICINE,
        prompt="Test medical case",
        llm_response="Test response",
        model_type=ModelType.GPT_4O_MINI,
        generation_config=BaseConfig(),
        verification_info={'medical_content': medical_content},
        machine_info=MachineInfo(
            hostname="test",
            cpu_info={'processor': 'test', 'cores': 4},
            memory_info={'total': 1000, 'available': 500},
            platform="test",
            gpu_info=None,
        ),
        gold_standard_solution="Sample solution for testing",
        verification_config=BaseConfig(),
    )


async def demonstrate_valid_case():
    """Demonstrate verification of a valid medical case."""
    verifier = MedicalVerifier()
    
    # Create a valid STEMI case
    valid_case = create_test_response({
        'symptoms': 'Severe chest pain, shortness of breath',
        'diagnosis': 'Acute STEMI',
        'treatment': 'Emergency PCI, Aspirin 325mg',
        'icd_codes': 'I21.0',
    })
    
    async with verifier:
        result = await verifier.verify(valid_case)
    
    print("\n=== Valid STEMI Case ===")
    print(f"Status: {result.status}")
    print(f"Confidence Score: {result.metadata['confidence_score']:.2f}")
    print("Validations:")
    for validation in result.metadata['validations']:
        print(f"- {validation['type']}: {validation['validation']}")


async def demonstrate_invalid_case():
    """Demonstrate verification of an invalid medical case."""
    verifier = MedicalVerifier()
    
    # Create a case with invalid ICD code and missing fields
    invalid_case = create_test_response({
        'symptoms': 'Fever, cough',
        'diagnosis': 'Pneumonia',
        # Missing treatment field
        'icd_codes': 'XXX',  # Invalid ICD code
    })
    
    async with verifier:
        result = await verifier.verify(invalid_case)
    
    print("\n=== Invalid Case ===")
    print(f"Status: {result.status}")
    print(f"Error Messages: {result.error_message}")


async def demonstrate_drug_interactions():
    """Demonstrate drug interaction checking."""
    verifier = MedicalVerifier()
    
    # Create a case with potential drug interactions
    interaction_case = create_test_response({
        'symptoms': 'Multiple conditions requiring anticoagulation',
        'diagnosis': 'Atrial fibrillation with arthritis',
        'treatment': 'warfarin 5mg daily, aspirin 81mg daily',
        'icd_codes': 'I48.91',
    })
    
    async with verifier:
        result = await verifier.verify(interaction_case)
    
    print("\n=== Drug Interaction Case ===")
    print(f"Status: {result.status}")
    print("Drug Interactions:")
    for validation in result.metadata['validations']:
        if validation['type'] == 'drug_interactions':
            for interaction in validation['interactions']:
                print(f"- Warning: {interaction['warning']}")
                print(f"  Drugs: {', '.join(interaction['drugs'])}")


async def demonstrate_batch_verification():
    """Demonstrate batch verification of multiple cases."""
    verifier = MedicalVerifier()
    
    # Create multiple test cases
    cases = [
        # Case 1: Valid STEMI case
        create_test_response(
            {
                'symptoms': 'Chest pain',
                'diagnosis': 'STEMI',
                'treatment': 'PCI, Aspirin',
                'icd_codes': 'I21.0',
            },
            "case_1"
        ),
        # Case 2: Invalid ICD code
        create_test_response(
            {
                'symptoms': 'Headache',
                'diagnosis': 'Migraine',
                'treatment': 'Sumatriptan',
                'icd_codes': 'XXX',
            },
            "case_2"
        ),
        # Case 3: Drug interaction case
        create_test_response(
            {
                'symptoms': 'Multiple conditions',
                'diagnosis': 'AF with high cholesterol',
                'treatment': 'warfarin, simvastatin, clarithromycin',
                'icd_codes': 'I48.91',
            },
            "case_3"
        ),
    ]
    
    async with verifier:
        results = await verifier.verify_batch(cases)
    
    print("\n=== Batch Verification Results ===")
    for i, result in enumerate(results, 1):
        print(f"\nCase {i}:")
        print(f"Status: {result.status}")
        if result.error_message:
            print(f"Errors: {result.error_message}")
        if result.metadata.get('validations'):
            print("Validations:")
            for validation in result.metadata['validations']:
                print(f"- {validation['type']}")


async def main():
    """Run all demonstration examples."""
    print("=== Medical Verifier Demonstrations ===")
    
    await demonstrate_valid_case()
    await demonstrate_invalid_case()
    await demonstrate_drug_interactions()
    await demonstrate_batch_verification()


if __name__ == "__main__":
    asyncio.run(main()) 