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
from typing import List, Union

from camel.workforce import UnitWorkforce, Workforce


def get_workforces_info(
    workforces: List[Union[Workforce, UnitWorkforce]],
) -> dict:
    workforce_info = {}
    for workforce in workforces:
        workforce_info[workforce.workforce_id] = workforce.description
    return workforce_info


def compose(subtask_result: List[str]):
    pass
