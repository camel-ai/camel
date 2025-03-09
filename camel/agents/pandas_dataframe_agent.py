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

from typing import Any, Dict, Optional, Union

import pandas as pd

from camel.loaders import PandasReader

# AgentOps decorator setting
try:
    import os

    if os.getenv("AGENTOPS_API_KEY") is not None:
        from agentops import track_agent
    else:
        raise ImportError
except (ImportError, AttributeError):
    from camel.utils import track_agent


@track_agent(name="PandasDataFrameAgent")
class PandasDataFrameAgent:
    def __init__(
        self,
        data: Union[pd.DataFrame, str],
        config: Optional[Dict[str, Any]] = None,
    ):
        r"""
        Initializes the PandasDataFrameAgent for
         AI-powered querying of a pandas DataFrame.

        Args:
            data (Union[pd.DataFrame, str]): Loading the data from.
            config (Optional[Dict[str, any]]):
             Configuration for the LLM. Defaults to OpenAI.

        Raises:
            ValueError: If no LLM is specified in config
             and OPENAI_API_KEY is not set.
        """
        reader = PandasReader()
        self.df = reader.load(data)

        if config is None:
            config = {}
        if "llm" not in config:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY Required")
            from pandasai.llm import OpenAI  # type: ignore[import-untyped]

            config["llm"] = OpenAI(api_token=api_key)

        # Initialize SmartDataframe for AI querying
        from pandasai import SmartDataframe

        self.smart_df = SmartDataframe(self.df, config=config)

    def chat(self, query: str) -> pd.DataFrame:
        return self.smart_df.chat(query)
