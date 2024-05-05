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

from camel.types import ModelType
from camel.utils import role_playing_with_function


def main(model_type=ModelType.GPT_4, chat_turn_limit=10) -> None:
    role_playing_with_function(
        model_type=model_type, chat_turn_limit=chat_turn_limit,
        assistant_role_name="function calling operator",
        user_role_name="human",
        task_prompt=(
                     "search basketball course from coursera. and help me "
                     "to find a job by jobsearch to be a basketball coach in "
                     "london.")
    )


if __name__ == "__main__":
    main()
