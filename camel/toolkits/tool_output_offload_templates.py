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

r"""String templates for ToolOutputOffloadToolkit."""

# ========= Auto-offload replacement template =========

REPLACEMENT_CONTENT = (
    "[OFFLOADED OUTPUT - ID: {offload_id}]\n\n"
    "Summary: {summary}\n\n"
    "Original length: {original_length} chars\n"
    'Use retrieve_offloaded_tool_output("{offload_id}") to get full content.'
)
