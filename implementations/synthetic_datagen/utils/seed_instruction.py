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
from typing import List, Optional
from uuid import uuid4


class Instance:
    def __init__(self, input: str, output: str):
        self.input = input
        self.output = output

    def __str__(self):
        return f"Input: {self.input[:50]}... | Output: {self.output[:50]}..."

    def __repr__(self):
        return (
            f"InContextExample(input='{self.input[:50]}...',"
            f" output='{self.output[:50]}...')"
        )


class SeedInstruction:
    def __init__(
        self,
        instruction: str,
        instances: List[Instance],
        id: Optional[str] = None,
        short_name: Optional[str] = None,
        is_classification: bool = False,
    ):
        self.id = id or uuid4()
        self.short_name = short_name or uuid4()
        self.instruction = instruction
        self.instances = instances
        self.is_classification = is_classification

    def __str__(self):
        return f"Task {self.id}: {self.short_name}"

    def __repr__(self):
        return (
            f"Task(id='{self.id}', short_name='{self.short_name}',"
            " is_classification={self.is_classification})"
        )
