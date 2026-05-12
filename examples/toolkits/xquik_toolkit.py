# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

import os

from camel.toolkits import XquikToolkit
from camel.toolkits.xquik_toolkit import (
    xquik_get_trends,
    xquik_get_user_info,
    xquik_search_tweets,
)


def main() -> None:
    r"""Run read-only X (Twitter) lookups with XquikToolkit.

    Set ``XQUIK_API_KEY`` before running this example.
    """
    if not os.environ.get("XQUIK_API_KEY"):
        raise RuntimeError("Set XQUIK_API_KEY before running this example.")

    toolkit = XquikToolkit()
    tool_names = [tool.get_function_name() for tool in toolkit.get_tools()]
    print(f"Available Xquik tools: {', '.join(tool_names)}")

    print(
        xquik_search_tweets(
            query="CAMEL-AI -is:retweet",
            max_results=10,
            sort_order="Latest",
        )
    )
    print(xquik_get_user_info("CamelAIOrg"))
    print(xquik_get_trends(woeid=1, count=5))


if __name__ == "__main__":
    main()
