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
from typing import Dict, List, Optional

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit


class IgnoreRiskToolkit(BaseToolkit):
    r"""A toolkit for ignoring risks associated with functions.

    Args:
        function_names (Optional[List[str]]): A list of function names to
            ignore risks for. (default: :obj:`None`)
        verbose (Optional[bool]): Whether to print verbose output.
            (default: :obj:`False`)
    """

    def __init__(
        self,
        function_name: Optional[List[str]] = None,
        verbose: Optional[bool] = False,
    ):
        self.verbose = verbose
        self.function_names = function_name or []
        self.ignored_risks: Dict[str, str] = dict()

    def add(self, name: str):
        r"""Adds a function to the toolkit.

        Args:
            name (str): The name of the function to add.
        """
        self.function_names.append(name)

    def ignore_risk(self, name: str, reason: str) -> str:
        r"""Force ignores the risk associated with named function. This ONLY
        ignores the RISK for the NEXT Function Call.

        Args:
            name (str): The name of the function to ignore.
            reason (str): A brief explanation of the reasoning
                behind the decision to ignore the risk.
        """
        if name not in self.function_names:
            raise ValueError(f"Function {name} not found in the toolkit.")

        self.ignored_risks[name] = reason
        if self.verbose:
            print(f"Ignoring risk for function {name}: {reason}")
        return f"Ignored risk for function {name}!"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [FunctionTool(self.ignore_risk)]
