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
import tempfile

import pandas as pd  # type: ignore[import-untyped]
import pytest
from pandasai.llm import OpenAI  # type: ignore[import-untyped]

from camel.loaders import PandasReader


def test_load_dataframe():
    reader = PandasReader()
    sales_by_country = {
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
    df = reader.load(pd.DataFrame(sales_by_country))
    # Test that the dataframe was loaded correctly
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (10, 2)
    assert "country" in df.columns
    assert "sales" in df.columns
    assert df["sales"].sum() == 36200


def test_multi_column_dataframe():
    reader = PandasReader()
    sales_by_country = {
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
        "profit": [
            1000,
            500,
            400,
            600,
            300,
            200,
            250,
            300,
            800,
            1200,
        ],
    }
    df = reader.load(pd.DataFrame(sales_by_country))
    # Test that the dataframe was loaded correctly with multiple columns
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (10, 3)
    assert "country" in df.columns
    assert "sales" in df.columns
    assert "profit" in df.columns
    assert df["profit"].sum() == 5550


def test_load_from_url():
    """Test loading from a file path instead of URL to avoid hanging."""
    reader = PandasReader()

    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
        # Write sample data to the file
        tmp.write(
            b"Country,Population,Area\nUSA,331000000,9834000\nChina,1444000000,9597000\nIndia,1393000000,3287000\n"
        )
        tmp_path = tmp.name

    try:
        # Test loading from the file
        df = reader.load(tmp_path)
        assert isinstance(df, pd.DataFrame)
        assert "Country" in df.columns
        assert df.shape == (3, 3)
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@pytest.mark.skipif(
    os.getenv("OPENAI_API_KEY") is None,
    reason="OPENAI_API_KEY environment variable not set",
)
def test_with_llm():
    """Test with LLM explicitly configured."""
    llm_config = {
        "llm": OpenAI(
            api_token=os.getenv("OPENAI_API_KEY"),
        )
    }
    reader = PandasReader(config=llm_config)
    sales_by_country = {
        "country": ["United States", "United Kingdom", "China"],
        "sales": [5000, 3200, 7000],
    }
    df = reader.load(pd.DataFrame(sales_by_country))
    # With LLM config, should return a SmartDataframe
    from pandasai import SmartDataframe

    assert isinstance(df, SmartDataframe)

    # Test chat functionality if needed
    if os.getenv("OPENAI_API_KEY"):
        resp = df.chat("Which country has the highest sales?")
        # The response format can vary, so we just check that we got something
        assert resp is not None
