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
from pathlib import Path
from typing import ClassVar

from camel.datasets import FewShotGenerator, StaticDataset
from camel.logger import get_logger
from camel.verifiers import PythonVerifier

logger = get_logger(__name__)


seed_data = [
    {
        "question": "What is 2 + 2?",
        "rationale": "result = 2 + 2\nprint(result)",
        "final_answer": "4",
    },
    {
        "question": "What is 10 / 2?",
        "rationale": "result = 10 / 2\nprint(result)",
        "final_answer": "5.0",
    },
]


class MockChatAgent:
    def step(self, prompt, response_format):
        """Simulates LLM response with executable Python rationale."""

        class MockResponse:
            msgs: ClassVar = [
                type(
                    "MockMessage",
                    (),
                    {
                        "parsed": {
                            "question": "What is 3 * 3?",
                            "rationale": "result = 3 * 3\nprint(result)",
                        }
                    },
                )
            ]

        return MockResponse()


async def main():
    seed_dataset = StaticDataset(data=seed_data)

    verifier = PythonVerifier(required_packages=["numpy"])
    await verifier.setup()

    agent = MockChatAgent()

    generator = FewShotGenerator(
        seed_dataset=seed_dataset, verifier=verifier, agent=agent
    )

    new_data = await generator.generate_new(n=2)

    for dp in new_data:
        print(dp)

    generator.save_to_jsonl(Path("generated_data.jsonl"))

    await verifier.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
