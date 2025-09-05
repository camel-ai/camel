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

from camel.societies.workforce.workforce import Workforce
from camel.tasks.task import Task


async def main():
    base_url = "http://localhost:10000"
    # Extra keyword arguments passed into httpx.AsyncClient
    http_kwargs = {
        "timeout": 30.0,
        "headers": {
            "User-Agent": "workforce-a2a-client/0.1",
        },
    }

    workforce = Workforce("A2A Example Workforce")
    await workforce.add_a2a_agent_worker(
        base_url=base_url,
        http_kwargs=http_kwargs,
    )

    task1 = Task(content="how much is 10 USD in INR")
    result1 = await workforce.process_task_async(task1)
    print(f"Task 1 result: {result1.result}")


if __name__ == "__main__":
    asyncio.run(main())
