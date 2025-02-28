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
from typing import Dict, Any
import asyncio

from camel.extractors.medicine import MedicineExtractor


async def demonstrate_standard_format():
    """Demonstrate extraction from standard formatted medical cases."""
    extractor = MedicineExtractor()
    
    # Example 1: Complete standard format
    standard_case = """
    Symptoms: Severe chest pain radiating to left arm and jaw, shortness of breath, sweating
    Diagnosis: Acute Myocardial Infarction (STEMI)
    Treatment: Emergency PCI, Aspirin 325mg, Clopidogrel 600mg loading dose
    Clinical Reasoning: ST elevation in leads V1-V4, elevated troponin, typical symptoms
    References: ACC/AHA Guidelines for STEMI Management 2023
    ICD Codes: I21.0
    Difficulty: High
    """
    
    # Example 2: Alternative headers format
    alternative_headers = """
    Chief Complaints: Fever 39.5°C, productive cough, fatigue for 5 days
    Assessment: Community Acquired Pneumonia
    Management: Amoxicillin-Clavulanate 875/125mg BID for 7 days
    Rationale: Focal consolidation on CXR, elevated WBC, normal procalcitonin
    Citations: Infectious Diseases Society of America Guidelines
    Diagnosis Codes: J18.9
    Complexity: Moderate
    """
    
    async with extractor:
        result1 = await extractor.extract(
            standard_case,
            context={
                'specialty': 'Cardiology',
                'evidence_level': 'A',
            }
        )
        result2 = await extractor.extract(
            alternative_headers,
            context={
                'specialty': 'Internal Medicine',
                'evidence_level': 'B',
            }
        )
    
    return result1, result2


async def demonstrate_free_text():
    """Demonstrate extraction from free-text medical cases."""
    extractor = MedicineExtractor()
    
    # Example 1: Natural language case description
    narrative_case = """
    A 45-year-old male patient presents with severe headache, photophobia, 
    and nausea lasting for the past 24 hours. The patient reports similar 
    episodes in the past. They were diagnosed with chronic migraine. 
    The recommended treatment includes sumatriptan 50mg and preventive 
    therapy with propranolol 40mg daily.
    """
    
    # Example 2: Clinical note style
    clinical_note = """
    Patient reports persistent joint pain and morning stiffness affecting 
    multiple joints, particularly hands and knees, lasting >1 hour. 
    Symptoms include reduced range of motion and joint swelling.
    
    The likely diagnosis is Rheumatoid Arthritis based on clinical presentation,
    positive RF, and elevated CRP.
    
    Treated with Methotrexate 15mg weekly, folic acid supplementation, 
    and NSAIDs for symptomatic relief.
    """
    
    async with extractor:
        result1 = await extractor.extract(
            narrative_case,
            context={
                'specialty': 'Neurology',
                'evidence_level': 'B',
            }
        )
        result2 = await extractor.extract(
            clinical_note,
            context={
                'specialty': 'Rheumatology',
                'evidence_level': 'B',
            }
        )
    
    return result1, result2


async def demonstrate_mixed_format():
    """Demonstrate extraction from mixed format medical cases."""
    extractor = MedicineExtractor()
    
    # Example: Combining structured and free text
    mixed_case = """
    Patient presents with acute onset of confusion, fever 38.9°C, 
    and neck stiffness.
    
    Diagnosis: Bacterial Meningitis
    Treatment: 
    - Ceftriaxone 2g IV q12h
    - Vancomycin 15-20mg/kg IV q8-12h
    - Dexamethasone 10mg IV q6h
    
    The patient was diagnosed based on CSF analysis showing elevated 
    protein, low glucose, and neutrophilic pleocytosis.
    
    ICD Codes: G00.9
    Level: High
    References: 
    1. IDSA Guidelines for Bacterial Meningitis
    2. Neurology Clinical Practice 2023
    """
    
    async with extractor:
        result = await extractor.extract(
            mixed_case,
            context={
                'specialty': 'Infectious Disease',
                'evidence_level': 'A',
            }
        )
    
    return result


def print_extraction_result(case_type: str, result: Dict[str, Any]):
    """Helper function to print extraction results."""
    print(f"\n=== {case_type} ===")
    print("Question (Symptoms):", result['question'])
    print("Final Answer (Diagnosis):", result['final_answer'])
    print("Ground Truth (Treatment):", result['ground_truth'])
    print("Clinical Reasoning:", result['chain_of_thought'])
    print("Difficulty:", result['difficulty'])
    print("\nMetadata:")
    for key, value in result['metadata'].items():
        if value:
            print(f"- {key}: {value}")


async def main():
    """Run all demonstration examples."""
    # Standard format examples
    standard_result1, standard_result2 = await demonstrate_standard_format()
    print_extraction_result("Standard Format - Cardiac Case", standard_result1)
    print_extraction_result("Standard Format - Pneumonia Case", standard_result2)
    
    # Free text examples
    free_text_result1, free_text_result2 = await demonstrate_free_text()
    print_extraction_result("Free Text - Migraine Case", free_text_result1)
    print_extraction_result("Free Text - Rheumatology Case", free_text_result2)
    
    # Mixed format example
    mixed_result = await demonstrate_mixed_format()
    print_extraction_result("Mixed Format - Meningitis Case", mixed_result)


if __name__ == "__main__":
    asyncio.run(main()) 