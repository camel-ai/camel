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
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import OpenAIModel, StubModel
from camel.terminators import ResponseWordsTerminator
from camel.types import ModelType


def _make_agent() -> ChatAgent:
    return ChatAgent(
        model=StubModel(ModelType.STUB),
        response_terminators=[ResponseWordsTerminator(words_dict={"stop": 2})],
    )


def _stop_response():
    return [
        BaseMessage.make_assistant_message(
            role_name="assistant",
            content="stop",
        )
    ]


def test_clone_response_terminators_have_independent_identity():
    source = _make_agent()
    first = source.clone()
    second = source.clone()

    assert first.response_terminators is not source.response_terminators
    assert second.response_terminators is not source.response_terminators
    assert first.response_terminators is not second.response_terminators
    assert first.response_terminators[0] is not source.response_terminators[0]
    assert second.response_terminators[0] is not source.response_terminators[0]
    assert first.response_terminators[0] is not second.response_terminators[0]


def test_clone_response_terminator_counts_are_independent():
    source = _make_agent()
    first = source.clone()
    second = source.clone()

    assert first.response_terminators[0].is_terminated(_stop_response()) == (
        False,
        None,
    )
    assert second.response_terminators[0].is_terminated(_stop_response()) == (
        False,
        None,
    )


def test_resetting_clone_does_not_reset_another_clone_terminator():
    source = _make_agent()
    first = source.clone()
    second = source.clone()

    assert first.response_terminators[0].is_terminated(_stop_response()) == (
        False,
        None,
    )
    second.reset()

    terminated, reason = first.response_terminators[0].is_terminated(
        _stop_response()
    )
    assert terminated
    assert reason is not None


def test_reset_clears_response_chain_state_for_shared_models():
    model = OpenAIModel(
        model_type=ModelType.GPT_4O_MINI,
        api_mode="responses",
        api_key="test-key",
    )
    agent = ChatAgent(model=model)
    session_key = model._get_response_chain_session_key()
    model._save_response_chain_state(session_key, "resp_previous", 3)

    agent.reset()

    assert session_key not in model._responses_previous_response_id_by_session
    assert session_key not in model._responses_last_message_count_by_session
