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
"""
Example: Subscribe to callbacks in Workforce

Includes:
- Custom callback `PrintCallback` that logs key lifecycle events.
- Subscribe callbacks via the `callbacks` parameter when constructing a
  `Workforce`.
"""

import asyncio

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.models import ModelFactory
from camel.societies.workforce.workforce import Workforce
from camel.societies.workforce.workforce_logger import WorkforceLogger
from camel.types import ModelPlatformType, ModelType

logger = get_logger(__name__)


def build_teacher_agent() -> ChatAgent:
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEEPSEEK,
        model_type=ModelType.DEEPSEEK_CHAT,
    )
    return ChatAgent(
        system_message="You are a teacher of physics", model=model
    )


def build_student_agent() -> ChatAgent:
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEEPSEEK,
        model_type=ModelType.DEEPSEEK_CHAT,
    )
    return ChatAgent(
        system_message="You are a student of physics", model=model
    )


async def run_demo() -> None:
    logger_callback = WorkforceLogger(workforce_id="workforce-logger-demo")
    callbacks = [logger_callback]

    workforce = Workforce(
        "Workforce Callbacks Demo",
        callbacks=callbacks,
        use_structured_output_handler=True,
    )

    teacher = build_teacher_agent()
    student = build_student_agent()
    workforce.add_single_agent_worker("Teacher Worker", teacher)
    workforce.add_single_agent_worker("Student Worker", student)
    workforce.add_main_task(
        '''The teacher set an exam question about physics and have the
        students answer it. The teacher will then grade the students
        answer and provide feedback if needed.'''
    )

    # Start Workforce and wait for completion (timeout to avoid hanging)
    wf_task = asyncio.create_task(workforce.start())
    try:
        await asyncio.wait_for(wf_task, timeout=180.0)
    except asyncio.TimeoutError:
        logger.warning("Workforce run timed out; stopping...")
        workforce.stop()

    # Read KPIs and a simple "tree"
    print(f"KPIs: {workforce.get_workforce_kpis()}")
    print(f"Tree: {workforce.get_workforce_log_tree()}")


if __name__ == "__main__":
    asyncio.run(run_demo())
