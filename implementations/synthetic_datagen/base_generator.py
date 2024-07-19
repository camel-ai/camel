# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseDataGenerator(ABC):
    """
    An abstract base class for all synthetic data generators.
    """

    @abstractmethod
    def generate(self):
        raise NotImplementedError(
            "This method must be implemented by subclasses."
        )

    @abstractmethod
    def curate(self):
        raise NotImplementedError(
            "This method must be implemented by subclasses."
        )

    @abstractmethod
    def evaluate(self) -> Dict[str, Any]:
        raise NotImplementedError(
            "This method must be implemented by subclasses."
        )
