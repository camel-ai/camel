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
import logging
import re
from typing import Any, Dict, Optional

from camel.models import NvidiaModelV2
from camel.types import ModelType
from synthetic_datagen.agent_systems.base_agent_system import (
    BaseEvalAgentSystem,
    SyntheticDatum,
)

logger = logging.getLogger(__name__)


USER_PROMPT_TEMPLATE = """
### Instruction:
{instruction}
### Input:
{input}
"""


class NemotronRewardEvalAgent(BaseEvalAgentSystem):
    def __init__(self) -> None:
        self.nemotron = NvidiaModelV2(model_type=ModelType.NEMOTRON_4_REWARD)

    def run_eval(
        self, synthetic_datum: SyntheticDatum
    ) -> Optional[Dict[str, Any]]:
        message = [
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    instruction=synthetic_datum.instruction,
                    input=synthetic_datum.input,
                ),
            },
            {
                "role": "assistant",
                "content": synthetic_datum.output,
            },
        ]
        response = self.nemotron.run(message)
        print(response)
        match = re.search(r"content='(.*?)'", str(response))
        if not match:
            logger.error("Failed to parse response from Nemotron. {response}")
            return None

        scores_str = match.group(1)
        logger.info(f"Scores: {scores_str}")
        scores = {
            item.split(":")[0]: float(item.split(":")[1])
            for item in scores_str.split(",")
        }

        return scores
