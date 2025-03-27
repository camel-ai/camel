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
import json

from colorama import Fore

from camel.agents.deductive_reasoner_agent import DeductiveReasonerAgent


def main(model=None) -> None:
    # Construct deductive reasoner agent
    insight_agent = DeductiveReasonerAgent(model=model)

    starting_state = "The current empty website."
    target_state = "A website with search capabilities."
    conditions_and_quality = insight_agent.deduce_conditions_and_quality(
        starting_state=starting_state, target_state=target_state
    )
    print(
        Fore.GREEN
        + "Conditions and quality from the starting state:\n"
        + f"{json.dumps(conditions_and_quality, 
            indent=4, ensure_ascii=False)}",
        Fore.RESET,
    )


if __name__ == "__main__":
    main()
