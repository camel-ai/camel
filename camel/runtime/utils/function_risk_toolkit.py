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
from typing import List, Optional

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit


class FunctionRiskToolkit(BaseToolkit):
    r"""A toolkit for assessing the risk associated with functions.

    Args:
        verbose (Optional[bool]): Whether to print verbose output.
            (default: :obj:`False`)
    """

    def __init__(self, verbose: Optional[bool] = False):
        self.verbose = verbose

    def function_risk(self, score: int, reason: str):
        r"""Provides an assessment of the potential risk associated
            with a function.

        Args:
            score (int): The risk level associated with the function,
                ranging from 1 to 3:
                    - 1: No harm
                        (e.g., simple math operations, content searches)
                    - 2: Minimal harm (e.g., accessing user files)
                    - 3: Risk present
                        (e.g., deleting files, modifying the file system)
            reason (str): A brief explanation of the reasoning behind
                the assigned score, describing the specific aspects that
                contribute to the assessed risk.
        """
        if self.verbose:
            print(f"Function risk assessment: {reason} (score: {score})")

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [FunctionTool(self.function_risk)]
