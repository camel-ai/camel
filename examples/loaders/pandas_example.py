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


import os

import pandas as pd
from pandasai.llm import OpenAI  # type: ignore[import-untyped]

from camel.loaders import PandasReader

# Create sample data
sales_by_country = pd.DataFrame(
    {
        "country": [
            "United States",
            "United Kingdom",
            "France",
            "Germany",
            "Italy",
            "Spain",
            "Canada",
            "Australia",
            "Japan",
            "China",
        ],
        "sales": [
            5000,
            3200,
            2900,
            4100,
            2300,
            2100,
            2500,
            2600,
            4500,
            7000,
        ],
    }
)

# Example 1: Using PandasReader without an LLM (default behavior)
print("Example 1: PandasReader without LLM")
reader_no_llm = PandasReader()
# Without an LLM, load() returns a regular pandas DataFrame
df_no_llm = reader_no_llm.load(sales_by_country)
print(f"Loaded DataFrame shape: {df_no_llm.shape}")
print("Top 5 countries by sales:")
print(df_no_llm.sort_values(by="sales", ascending=False).head(5))
print()

# Example 2: Using PandasReader with an LLM configuration
print("Example 2: PandasReader with LLM")
# Only run this example if OPENAI_API_KEY is set
if os.getenv("OPENAI_API_KEY"):
    llm_config = {
        "llm": OpenAI(
            api_token=os.getenv("OPENAI_API_KEY"),
        )
    }
    reader_with_llm = PandasReader(config=llm_config)
    # With an LLM, load() returns a SmartDataframe
    df_with_llm = reader_with_llm.load(sales_by_country)
    print("Querying data with LLM:")
    print(df_with_llm.chat("Which are the top 5 countries by sales?"))
else:
    print("Skipping LLM example: OPENAI_API_KEY environment variable not set")

'''
Example output:

Example 1: PandasReader without LLM
Loaded DataFrame shape: (10, 2)
Top 5 countries by sales:
          country  sales
9           China   7000
0   United States   5000
8           Japan   4500
3         Germany   4100
1  United Kingdom   3200

Example 2: PandasReader with LLM
Querying data with LLM:
===============================================================================
          country  sales
9           China   7000
0   United States   5000
8           Japan   4500
3         Germany   4100
1  United Kingdom   3200
===============================================================================
'''
