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

from camel.loaders.scrapegraph_loader import ScrapeGraphAILoader

from .apify_loader import ApifyLoader
from .base_io import File, create_file, create_file_from_raw_bytes
from .chunkr_loader import ChunkrLoader, ChunkrLoaderConfig
from .crawl4ai_loader import Crawl4AILoader
from .firecrawl_loader import FirecrawlLoader
from .jina_url_loader import JinaURLLoader
from .markitdown_loader import MarkItDownLoader
from .mineru_loader import MinerULoader
from .mistral_loader import MistralLoader
from .unstructured_io import UnstructuredIO

ScrapeGraphAI = ScrapeGraphAILoader

__all__ = [
    'ApifyLoader',
    'ChunkrLoader',
    'ChunkrLoaderConfig',
    'Crawl4AILoader',
    'File',
    'FirecrawlLoader',
    'JinaURLLoader',
    'MarkItDownLoader',
    'MinerULoader',
    'MistralLoader',
    'ScrapeGraphAI',
    'ScrapeGraphAILoader',
    'UnstructuredIO',
    'create_file',
    'create_file_from_raw_bytes',
]


def __getattr__(name: str):
    if name == 'PandasReader':
        raise ImportError(
            "PandasReader has been removed from camel.loaders. "
            "The pandasai dependency limited pandas to version 1.5.3. "
            "Please use ExcelToolkit from camel.toolkits instead for "
            "handling structured data."
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
