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
# ruff: noqa: I001
from .openai_function import (
    OpenAIFunction,
    get_openai_function_schema,
    get_openai_tool_schema,
)
from .open_api_specs.security_config import openapi_security_config


from .math_toolkit import MathToolkit, MATH_FUNCS
from .search_toolkit import SearchToolkit, SEARCH_FUNCS
from .weather_toolkit import WeatherToolkit, WEATHER_FUNCS
from .dalle_toolkit import DalleToolkit, DALLE_FUNCS

from .base import BaseToolkit
from .google_maps_toolkit import GoogleMapsToolkit
from .code_execution import CodeExecutionToolkit
from .github_toolkit import GithubToolkit
from .arxiv_toolkit import ArxivToolkit
from .linkedin_toolkit import LinkedInToolkit
from .reddit_toolkit import RedditToolkit
from .slack_toolkit import SlackToolkit
from .twitter_toolkit import TwitterToolkit
from .open_api_toolkit import OpenAPIToolkit
from .retrieval_toolkit import RetrievalToolkit

__all__ = [
    'BaseToolkit',
    'OpenAIFunction',
    'get_openai_function_schema',
    'get_openai_tool_schema',
    'openapi_security_config',
    'GithubToolkit',
    'MathToolkit',
    'GoogleMapsToolkit',
    'SearchToolkit',
    'SlackToolkit',
    'DalleToolkit',
    'TwitterToolkit',
    'WeatherToolkit',
    'RetrievalToolkit',
    'OpenAPIToolkit',
    'LinkedInToolkit',
    'RedditToolkit',
    'CodeExecutionToolkit',
    'ArxivToolkit',
    'MATH_FUNCS',
    'SEARCH_FUNCS',
    'WEATHER_FUNCS',
    'DALLE_FUNCS',
]
