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

from types import MethodType

from camel.models.xai_model import XAIModel
from camel.types import ModelType


def test_stream_to_chunks_handles_empty_stream():
    model = XAIModel.__new__(XAIModel)
    model.model_type = "grok-3"
    model._last_encrypted_content = None
    model._last_reasoning_content = None
    model._save_response_chain = lambda *_args, **_kwargs: None
    model._make_chunk = MethodType(lambda self, **kwargs: kwargs, model)

    assert list(XAIModel._stream_to_chunks(model, iter([]), 0)) == []


def test_grok_4_5_model_type_metadata():
    assert ModelType.XAI_GROK_4_5.value == "grok-4.5"
    assert ModelType.XAI_GROK_4_5.is_xai is True
    assert ModelType.XAI_GROK_4_5.token_limit == 500_000
    assert ModelType.XAI_GROK_4_5.support_native_tool_calling is True
    assert ModelType.XAI_GROK_4_5.support_native_structured_output is True
