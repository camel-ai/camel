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


import logging

import pandas as pd

from camel.loaders import PandaReader

logging.disable(logging.ERROR)


def main():
    reader = PandaReader()
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
    doc = reader.load(sales_by_country)
    print(doc.chat("Which are the top 5 countries by sales?"))


if __name__ == "__main__":
    main()
