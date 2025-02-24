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

import pandas as pd  # type: ignore[import-untyped]

from camel.loaders import PandaReader


def test_topk():
    reader = PandaReader()
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
    resp: pd.DataFrame = doc.chat("Which are the top 5 countries by sales?")
    print(resp["country"].tolist())
    assert resp["country"].tolist() == [
        "China",
        "United States",
        "Japan",
        "Germany",
        "United Kingdom",
    ]


def test_multi_rows():
    reader = PandaReader()
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
    doc = reader.load(pd.DataFrame(sales_by_country))
    resp: pd.DataFrame = doc.chat(
        "Calculate the profit margin for each country."
    )
    assert "profit_margin" in resp.columns
    assert resp["profit_margin"].tolist()[0] == 20.0


def test_load_from_url():
    reader = PandaReader()
    url = "https://raw.githubusercontent.com/cs109/2014_data/master/countries.csv"
    doc = reader.load(url)
    assert doc is not None
