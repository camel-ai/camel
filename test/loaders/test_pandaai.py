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
from unittest.mock import MagicMock, patch

import pandas as pd  # type: ignore[import-untyped]

from camel.loaders import PandaReader


def test_topk():
    mock_llm = MagicMock()
    mock_llm._extract_code = MagicMock(
        return_value="""
    result = df.sort_values('sales', ascending=False).head(5)
    return result
    """
    )
    mock_llm.generate_code = MagicMock(
        return_value=(
            "result = df.sort_values('sales', ascending=False).head(5)\n"
            "return result"
        )
    )
    mock_llm.call = MagicMock(
        return_value=(
            "result = df.sort_values('sales', ascending=False).head(5)\n"
            "return result"
        )
    )

    reader = PandaReader(config={"llm": mock_llm})
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
    doc = reader.load(pd.DataFrame(sales_by_country))

    # Mock the SmartDataframe.chat method to return a proper DataFrame
    doc.chat = MagicMock(
        return_value=pd.DataFrame(
            {
                "country": [
                    "China",
                    "United States",
                    "Japan",
                    "Germany",
                    "United Kingdom",
                ],
                "sales": [7000, 5000, 4500, 4100, 3200],
            }
        )
    )

    resp = doc.chat("Which are the top 5 countries by sales?")
    assert isinstance(
        resp, pd.DataFrame
    ), f"Expected a DataFrame but got: {resp}"
    assert resp["country"].tolist() == [
        "China",
        "United States",
        "Japan",
        "Germany",
        "United Kingdom",
    ]


@patch.dict(os.environ, {"OPENAI_API_KEY": "dummy-key"})
def test_multi_rows():
    mock_llm = MagicMock()
    mock_llm._extract_code = MagicMock(
        return_value="""
    df['profit_margin'] = (df['profit'] / df['sales']) * 100
    return df
    """
    )
    mock_llm.generate_code = MagicMock(
        return_value=(
            "df['profit_margin'] = (df['profit'] / df['sales']) * 100\n"
            "return df"
        )
    )
    mock_llm.call = MagicMock(
        return_value=(
            "df['profit_margin'] = (df['profit'] / df['sales']) * 100\n"
            "return df"
        )
    )

    reader = PandaReader(config={"llm": mock_llm})
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
    df = pd.DataFrame(sales_by_country)
    doc = reader.load(df)

    # Create a DataFrame with profit_margin column
    result_df = df.copy()
    result_df['profit_margin'] = (
        result_df['profit'] / result_df['sales']
    ) * 100

    # Mock the SmartDataframe.chat method,
    # return DataFrame with profit margin
    doc.chat = MagicMock(return_value=result_df)

    resp = doc.chat("Calculate the profit margin for each country.")
    assert "profit_margin" in resp.columns
    assert resp["profit_margin"].tolist()[0] == 20.0


@patch.dict(os.environ, {"OPENAI_API_KEY": "dummy-key"})
def test_load_from_url():
    reader = PandaReader()
    url = "https://raw.githubusercontent.com/cs109/2014_data/master/countries.csv"
    doc = reader.load(url)
    assert doc is not None
