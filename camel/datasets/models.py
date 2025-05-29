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
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DataPoint(BaseModel):
    r"""A single data point in the dataset.

    Attributes:
        question (str): The primary question or issue to be addressed.
        final_answer (str): The final answer.
        rationale (Optional[str]): Logical reasoning or explanation behind the
            answer. (default: :obj:`None`)
        metadata (Optional[Dict[str, Any]]): Additional metadata about the data
            point. (default: :obj:`None`)
    """

    question: str = Field(
        ..., description="The primary question or issue to be addressed."
    )
    final_answer: str = Field(..., description="The final answer.")
    rationale: Optional[str] = Field(
        default=None,
        description="Logical reasoning or explanation behind the answer.",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata about the data point."
    )

    def to_dict(self) -> Dict[str, Any]:
        r"""Convert DataPoint to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the DataPoint.
        """
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataPoint':
        r"""Create a DataPoint from a dictionary.

        Args:
            data (Dict[str, Any]): Dictionary containing DataPoint fields.

        Returns:
            DataPoint: New DataPoint instance.
        """
        return cls(**data)
