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

r"""Medical dataset module that provides specialized classes for handling medical data.
Inherits from base dataset module classes and adds medical domain-specific functionality.
"""

from typing import Dict, Optional, List, Any
import random
import json
import os
from camel.datasets.base import BaseDataset, DataPoint
from camel.logger import get_logger

logger = get_logger(__name__)

class MedicalDataPoint(DataPoint):
    r"""Medical domain data point class, inheriting from base DataPoint class.
    
    Extends DataPoint class to accommodate medical data specific needs with additional
    medical-specific fields and validation.

    Attributes:
        question (str): Combined case report and test results.
        rationale (str): Reasoning behind the diagnosis.
        final_answer (str): The medical diagnosis.
        difficulty (Optional[str]): Difficulty level of the medical case.
        metadata (Dict[str, Any]): Additional medical case information including
            patient demographics.
    """
    pass

class MedicalDataset(BaseDataset):
    r"""Medical domain dataset class, inheriting from base BaseDataset class.
    
    Provides specific functionality for handling medical datasets, including
    specialized data processing and validation for medical records.
    """
    
    async def setup(self) -> None:
        r"""Set up the dataset by processing raw data into MedicalDataPoint objects.

        This method:
        1. Calls parent setup for initialization
        2. Processes medical-specific data fields
        3. Creates MedicalDataPoint instances with proper field mapping
        """
        # Call parent setup to handle initialization flags
        await super().setup()
        
        if not self._raw_data:
            self.data = []
            return

        # Process raw data into MedicalDataPoint objects
        self.data = [
            MedicalDataPoint(
                # Combine case_report and test_results as the question
                question=f"{item.get('case_report', '')}\nTest Results: {item.get('test_results', '')}",
                # Empty rationale or generate one if needed
                rationale=self._generate_rationale(item),
                # Use diagnosis as the final answer
                final_answer=item.get("diagnosis", ""),
                # Set difficulty if available
                difficulty=item.get("difficulty", None),
                # Include all other fields as metadata
                metadata={
                    **{k: v for k, v in item.items()
                       if k not in ["case_report", "test_results", "diagnosis", "difficulty"]}
                }
            )
            for item in self._raw_data
        ]

    def _generate_rationale(self, item: Dict[str, Any]) -> str:
        r"""Generate a rationale based on the medical case information.

        Args:
            item (Dict[str, Any]): Raw medical case data.

        Returns:
            str: Generated rationale explaining the diagnosis.
        """
        return (
            f"Based on the patient's presentation and test results, "
            f"the diagnosis of {item.get('diagnosis', '')} was made."
        )

    def get_by_disease(self, disease_name: str) -> List[MedicalDataPoint]:
        r"""Retrieve all cases for a specific disease.

        Args:
            disease_name (str): Name of the disease to filter by.

        Returns:
            List[MedicalDataPoint]: List of matching medical cases.
        """
        return [
            MedicalDataPoint(**point.dict())
            for point in self.data
            if point.metadata and "Orpha_name" in point.metadata and 
            point.metadata["Orpha_name"].lower() == disease_name.lower()
        ]

def load_json_data(file_path: str) -> List[Dict[str, Any]]:
    r"""Load and parse JSON data file, handling potential formatting issues.
    
    Args:
        file_path (str): Path to the JSON file.
        
    Returns:
        List[Dict[str, Any]]: Parsed JSON data as a list of dictionaries.
    """
    try:
        # First try standard JSON loading
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure we return a list
            if not isinstance(data, list):
                data = [data]
            return data
    except json.JSONDecodeError:
        # If that fails, try to fix common JSON formatting issues
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Try to fix JSONL (one JSON object per line) format
        try:
            # Split by lines and parse each line separately
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            data = []
            for line in lines:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            if data:
                return data
        except Exception:
            pass
            
        # Try to fix by wrapping in array brackets if it looks like multiple objects
        try:
            if content.strip().startswith('{') and '}' in content:
                # Split by closing braces and try to parse each object
                parts = content.split('}')
                data = []
                for i, part in enumerate(parts[:-1]):  # Skip the last empty part
                    try:
                        if i > 0:
                            part = '{' + part
                        obj = json.loads(part + '}')
                        data.append(obj)
                    except Exception:
                        continue
                if data:
                    return data
        except Exception:
            pass
            
        # If all else fails, return an empty list
        print(f"Warning: Could not parse JSON data from {file_path}. Using empty dataset.")
        return []