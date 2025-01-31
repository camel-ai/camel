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

from camel.loaders import MinerU

mineru = MinerU()

# Single URL extraction
task = mineru.extract_url(
    url="https://www.camel-ai.org/about", is_ocr=True, enable_formula=False
)

print(task)
'''
===============================================================================

===============================================================================
'''

status = mineru.get_task_status(task["task_id"])
print(status)
'''
===============================================================================

===============================================================================
'''

# Batch URL extraction
files = [
    {
        "url": "https://www.camel-ai.org/about",
        "is_ocr": True,
        "data_id": "doc1",
    },
    {
        "url": "https://en.wikipedia.org/wiki/Autonomous_agent",
        "is_ocr": True,
        "data_id": "doc2",
    },
]

batch_id = mineru.batch_extract_urls(
    files=files, enable_formula=False, language="en"
)

print(batch_id)
'''
===============================================================================

===============================================================================
'''

batch_status = mineru.get_batch_status(batch_id)
print(batch_status)
'''
===============================================================================

===============================================================================
'''
