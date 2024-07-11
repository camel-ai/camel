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
from typing import Any

from synthetic_datagen.method_factory import (
    SyntheticDataGeneratorFactory,
    SyntheticDataGeneratorMethodType,
)


class DataGeneratorPipeline:
    """
    Manages the pipeline for synthetic data generation, curation
    and evaluation.
    """

    def __init__(
        self, spec: Any, method_type: SyntheticDataGeneratorMethodType
    ):
        """
        Initialize the pipeline with a specific generator
        type and specification.

        Args:
            spec (Any): Configuration for the generator.
            method_type (SyntheticDataGeneratorMethodType): Type of
            generator to use.
        """
        self.generator = SyntheticDataGeneratorFactory.create(
            method_type, spec
        )

    def run_generate(self):
        """Execute the data generation step of the pipeline."""
        self.generator.generate()

    def run_curate(self):
        """Execute the data curation step of the pipeline."""
        self.generator.curate()

    def run_evaluate(self):
        """Execute the data evaluation step of the pipeline."""
        self.generator.evaluate()
