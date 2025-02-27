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
from typing import Dict, List, Optional

from camel.datasets.base import BaseDataset, DataPoint


class MedicineDataset(BaseDataset):
    """A dataset for medical domain tasks.

    This dataset can handle various medical tasks including:
    - Disease diagnosis
    - Treatment recommendations
    - Drug interactions
    - Medical case analysis
    - Clinical guidelines
    - Medical research interpretation
    """

    def __init__(
        self,
        data_path: Optional[str] = None,
        categories: Optional[List[str]] = None,
        difficulty_levels: Optional[List[str]] = None,
        cache_dir: Optional[str] = None,
        max_cache_size: int = int(1e9),
        preload: bool = False,
        shuffle: bool = True,
        **kwargs,
    ):
        """Initialize the medical dataset.

        Args:
            data_path (Optional[str]): Path to the medical data files.
                (default: :obj:`None`)
            categories (Optional[List[str]]): List of medical categories
                to include.E.g. ['diagnosis', 'treatment', 'drug-interaction']
                (default: :obj:`None` for all categories)
            difficulty_levels (Optional[List[str]]): List of difficulty levels
                to include. E.g. ['basic', 'intermediate', 'advanced']
                (default: :obj:`None` for all levels)
            cache_dir (Optional[str]): Directory to cache dataset files.
                (default: :obj:`None`)
            max_cache_size (int): Maximum cache size in bytes.
                (default: :obj:`1e9` (1GB))
            preload (bool): Whether to preload dataset into memory.
                (default: :obj:`False`)
            shuffle (bool): Whether to shuffle dataset on load.
                (default: :obj:`True`)
            **kwargs: Additional dataset parameters.
        """
        super().__init__(
            cache_dir=cache_dir,
            max_cache_size=max_cache_size,
            preload=preload,
            shuffle=shuffle,
            **kwargs,
        )

        self._data_path = data_path
        self._categories = categories
        self._difficulty_levels = difficulty_levels
        self._data: List[Dict] = []  # Will store the loaded medical data

        # Additional metadata specific to medical domain
        self._metadata.update(
            {
                'data_path': self._data_path,
                'categories': self._categories,
                'difficulty_levels': self._difficulty_levels,
                'domain': 'medicine',
            }
        )

    async def setup(self) -> None:
        """Set up the medical dataset.

        This method:
        1. Loads medical data from specified path
        2. Filters by categories and difficulty levels
        3. Validates medical data format
        4. Initializes caching and shuffling
        """
        if self._is_setup:
            return

        await super().setup()

        try:
            # Here you would implement the logic to:
            # 1. Load medical data from files/database
            # 2. Parse and validate the data
            # 3. Filter by categories and difficulty levels
            # 4. Store in self._data
            pass

        except Exception as e:
            await self.cleanup()
            raise RuntimeError(f"Failed to setup medical dataset: {e}")

    def __len__(self) -> int:
        """Return the number of medical cases in the dataset."""
        return len(self._data)

    def __getitem__(self, idx: int) -> DataPoint:
        """Get a medical case from the dataset.

        Args:
            idx (int): Index of the medical case to get.

        Returns:
            DataPoint: A medical case data point containing:
                - question: Medical case description or query
                - final_answer: The diagnosis/treatment/recommendation
                - ground_truth: Verified medical solution
                - chain_of_thought: Clinical reasoning process
                - difficulty: Case complexity level
                - metadata: Additional medical context

        Raises:
            IndexError: If idx is out of bounds
        """
        if idx >= len(self) or idx < 0:
            raise IndexError(
                f"Index {idx} out of range for dataset of size {len(self)}"
            )

        medical_case = self._data[idx]

        return DataPoint(
            question=medical_case['description'],
            final_answer=medical_case['solution'],
            ground_truth=medical_case.get('verified_solution'),
            chain_of_thought=medical_case.get('clinical_reasoning'),
            difficulty=medical_case.get('complexity'),
            raw_markdown=medical_case.get('raw_content'),
            verified=medical_case.get('is_verified', False),
            metadata={
                'category': medical_case.get('category'),
                'speciality': medical_case.get('medical_speciality'),
                'required_expertise': medical_case.get('expertise_level'),
                'references': medical_case.get('medical_references'),
                'keywords': medical_case.get('medical_keywords'),
                'icd_codes': medical_case.get(
                    'icd_codes'
                ),  # International Classification of Diseases codes
                'evidence_level': medical_case.get('evidence_level'),
                'last_updated': medical_case.get('last_updated'),
            },
        )
