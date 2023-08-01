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
from typing import List

import pytest

from camel.agents import ChatAgent
from camel.agents.chat_agent import ChatRecord, FunctionCallingRecord
from camel.configs import ChatGPTConfig, FunctionCallingConfig
from camel.functions import MATH_FUNCS
from camel.generators import SystemMessageGenerator
from camel.messages import BaseMessage
from camel.typing import ModelType, RoleType, TaskType
from camel.utils import num_tokens_from_messages

parametrize = pytest.mark.parametrize('model', [
    ModelType.STUB,
    pytest.param(ModelType.GPT_3_5_TURBO, marks=pytest.mark.model_backend),
    pytest.param(ModelType.GPT_4, marks=pytest.mark.model_backend),
])


@parametrize
def test_chat_agent(model: ModelType):
    model_config = ChatGPTConfig()
    system_msg = SystemMessageGenerator(
        task_type=TaskType.AI_SOCIETY).from_dict(
            dict(assistant_role="doctor"),
            role_tuple=("doctor", RoleType.ASSISTANT),
        )
    assistant = ChatAgent(system_msg, model=model, model_config=model_config)

    assert str(assistant) == ("ChatAgent(doctor, "
                              f"RoleType.ASSISTANT, {str(model)})")

    assistant.reset()
    user_msg = BaseMessage(role_name="Patient", role_type=RoleType.USER,
                           meta_dict=dict(), content="Hello!")
    assistant_response = assistant.step(user_msg)

    assert isinstance(assistant_response.msgs, list)
    assert len(assistant_response.msgs) > 0
    assert isinstance(assistant_response.terminated, bool)
    assert assistant_response.terminated is False
    assert isinstance(assistant_response.info, dict)
    assert assistant_response.info['id'] is not None

    assistant.reset()
    token_limit = assistant.model_token_limit
    user_msg = BaseMessage(role_name="Patient", role_type=RoleType.USER,
                           meta_dict=dict(),
                           content="token" * (token_limit + 1))
    assistant_response = assistant.step(user_msg)

    assert isinstance(assistant_response.msgs, list)
    assert len(assistant_response.msgs) == 0
    assert isinstance(assistant_response.terminated, bool)
    assert assistant_response.terminated is True
    assert isinstance(assistant_response.info, dict)
    assert (assistant_response.info['termination_reasons'][0] ==
            "max_tokens_exceeded")


@pytest.mark.model_backend
def test_chat_agent_stored_messages():
    system_msg = BaseMessage(role_name="assistant",
                             role_type=RoleType.ASSISTANT, meta_dict=None,
                             content="You are a help assistant.")
    assistant = ChatAgent(system_msg)

    expected_stored_msg = [ChatRecord('system', system_msg)]
    assert assistant.stored_messages == expected_stored_msg

    user_msg = BaseMessage(role_name="User", role_type=RoleType.USER,
                           meta_dict=dict(), content="Tell me a joke.")
    assistant.update_messages("user", user_msg)
    expected_stored_msg = [
        ChatRecord('system', system_msg),
        ChatRecord('user', user_msg)
    ]
    assert assistant.stored_messages == expected_stored_msg

    illegal_role = "xxx"
    with pytest.raises(ValueError, match=f"Unsupported role {illegal_role}"):
        assistant.update_messages(illegal_role, user_msg)


@pytest.mark.model_backend
def test_chat_agent_preprocess_messages_window():
    system_msg = BaseMessage(role_name="assistant",
                             role_type=RoleType.ASSISTANT, meta_dict=None,
                             content="You are a help assistant.")
    assistant = ChatAgent(
        system_message=system_msg,
        model=ModelType.GPT_3_5_TURBO,
        message_window_size=1,
    )

    user_msg = BaseMessage(role_name="User", role_type=RoleType.USER,
                           meta_dict=dict(), content="Tell me a joke.")
    user_msg = ChatRecord("user", user_msg)
    system_msg = ChatRecord("system", system_msg)

    openai_messages, _ = assistant.preprocess_messages([system_msg, user_msg])
    assert len(openai_messages) == 2


@pytest.mark.model_backend
def test_chat_agent_step_exceed_token_number():
    system_msg = BaseMessage(role_name="assistant",
                             role_type=RoleType.ASSISTANT, meta_dict=None,
                             content="You are a help assistant.")
    assistant = ChatAgent(
        system_message=system_msg,
        model=ModelType.GPT_3_5_TURBO,
    )
    assistant.model_token_limit = 1

    user_msg = BaseMessage(role_name="User", role_type=RoleType.USER,
                           meta_dict=dict(), content="Tell me a joke.")
    user_msg_record = ChatRecord("user", user_msg)
    system_msg = ChatRecord("system", system_msg)
    msgs = [system_msg, user_msg_record]

    expect_openai_messages = [record.to_openai_message() for record in msgs]
    expect_num_tokens = num_tokens_from_messages(
        expect_openai_messages,
        assistant.model,
    )

    response = assistant.step(user_msg)
    assert len(response.msgs) == 0
    assert response.terminated
    assert response.info["num_tokens"] == expect_num_tokens


@pytest.mark.model_backend
@pytest.mark.parametrize('n', [1, 2, 3])
def test_chat_agent_multiple_return_messages(n):
    model_config = ChatGPTConfig(temperature=1.4, n=n)
    system_msg = BaseMessage("Assistant", RoleType.ASSISTANT, meta_dict=None,
                             content="You are a helpful assistant.")
    assistant = ChatAgent(system_msg, model_config=model_config)
    assistant.reset()
    user_msg = BaseMessage(role_name="User", role_type=RoleType.USER,
                           meta_dict=dict(), content="Tell me a joke.")
    assistant_response = assistant.step(user_msg)
    assert assistant_response.msgs is not None
    assert len(assistant_response.msgs) == n


@pytest.mark.model_backend
@pytest.mark.parametrize('n', [2])
def test_chat_agent_multiple_return_message_error(n):
    model_config = ChatGPTConfig(temperature=1.4, n=n)
    system_msg = BaseMessage("Assistant", RoleType.ASSISTANT, meta_dict=None,
                             content="You are a helpful assistant.")

    assistant = ChatAgent(system_msg, model_config=model_config)
    assistant.reset()

    user_msg = BaseMessage(role_name="User", role_type=RoleType.USER,
                           meta_dict=dict(), content="Tell me a joke.")
    assistant_response = assistant.step(user_msg)

    with pytest.raises(
            RuntimeError, match=("Property msg is only available "
                                 "for a single message in msgs.")):
        _ = assistant_response.msg


@pytest.mark.model_backend
def test_chat_agent_stream_output():
    system_msg = BaseMessage("Assistant", RoleType.ASSISTANT, meta_dict=None,
                             content="You are a helpful assistant.")
    user_msg = BaseMessage(role_name="User", role_type=RoleType.USER,
                           meta_dict=dict(), content="Tell me a joke.")

    stream_model_config = ChatGPTConfig(temperature=0, n=2, stream=True)
    stream_assistant = ChatAgent(system_msg, model_config=stream_model_config)
    stream_assistant.reset()
    stream_assistant_response = stream_assistant.step(user_msg)

    for msg in stream_assistant_response.msgs:
        assert len(msg.content) > 0

    stream_usage = stream_assistant_response.info["usage"]
    assert stream_usage["completion_tokens"] > 0
    assert stream_usage["prompt_tokens"] > 0
    assert stream_usage["total_tokens"] == stream_usage[
        "completion_tokens"] + stream_usage["prompt_tokens"]


@pytest.mark.model_backend
def test_set_output_language():
    system_message = BaseMessage(role_name="assistant",
                                 role_type=RoleType.ASSISTANT, meta_dict=None,
                                 content="You are a help assistant.")
    agent = ChatAgent(system_message=system_message,
                      model=ModelType.GPT_3_5_TURBO)
    assert agent.output_language is None

    # Set the output language to "Arabic"
    output_language = "Arabic"
    agent.set_output_language(output_language)

    # Check if the output language is set correctly
    assert agent.output_language == output_language

    # Verify that the system message is updated with the new output language
    updated_system_message = BaseMessage(
        role_name="assistant", role_type=RoleType.ASSISTANT, meta_dict=None,
        content="You are a help assistant."
        "\nRegardless of the input language, you must output text in Arabic.")
    assert agent.system_message.content == updated_system_message.content


@pytest.mark.model_backend
def test_set_multiple_output_language():
    system_message = BaseMessage(role_name="assistant",
                                 role_type=RoleType.ASSISTANT, meta_dict=None,
                                 content="You are a help assistant.")
    agent = ChatAgent(system_message=system_message,
                      model=ModelType.GPT_3_5_TURBO)

    # Verify that the length of the system message is kept constant even when
    # multiple set_output_language operations are called
    agent.set_output_language("Chinese")
    agent.set_output_language("English")
    agent.set_output_language("French")
    updated_system_message = BaseMessage(
        role_name="assistant", role_type=RoleType.ASSISTANT, meta_dict=None,
        content="You are a help assistant."
        "\nRegardless of the input language, you must output text in French.")
    assert agent.system_message.content == updated_system_message.content


@pytest.mark.model_backend
def test_token_exceed_return():
    system_message = BaseMessage(role_name="assistant",
                                 role_type=RoleType.ASSISTANT, meta_dict=None,
                                 content="You are a help assistant.")
    agent = ChatAgent(system_message=system_message,
                      model=ModelType.GPT_3_5_TURBO)

    expect_info = {
        "id": None,
        "usage": None,
        "termination_reasons": ["max_tokens_exceeded"],
        "num_tokens": 1000,
        "called_functions": [],
    }
    response = agent.step_token_exceed(1000, [])
    assert response.msgs == []
    assert response.terminated
    assert response.info == expect_info


@pytest.mark.model_backend
def test_function_enabled():
    system_message = BaseMessage(role_name="assistant",
                                 role_type=RoleType.ASSISTANT, meta_dict=None,
                                 content="You are a help assistant.")
    model_config = FunctionCallingConfig(
        functions=[func.as_dict() for func in MATH_FUNCS])
    agent_no_func = ChatAgent(system_message=system_message,
                              model_config=model_config, model=ModelType.GPT_4)
    agent_with_funcs = ChatAgent(system_message=system_message,
                                 model_config=model_config,
                                 model=ModelType.GPT_4,
                                 function_list=MATH_FUNCS)

    assert not agent_no_func.is_function_calling_enabled()
    assert agent_with_funcs.is_function_calling_enabled()


@pytest.mark.model_backend
def test_function_calling():
    system_message = BaseMessage(role_name="assistant",
                                 role_type=RoleType.ASSISTANT, meta_dict=None,
                                 content="You are a help assistant.")
    model_config = FunctionCallingConfig(
        functions=[func.as_dict() for func in MATH_FUNCS])
    agent = ChatAgent(system_message=system_message, model_config=model_config,
                      model=ModelType.GPT_4, function_list=MATH_FUNCS)

    ref_funcs = MATH_FUNCS

    assert len(agent.func_dict) == len(ref_funcs)
    model_config: FunctionCallingConfig = agent.model_config
    assert len(model_config.functions) == len(ref_funcs)

    user_msg = BaseMessage(role_name="User", role_type=RoleType.USER,
                           meta_dict=dict(),
                           content="Calculate the result of: 2*8-10.")
    agent_response = agent.step(user_msg)

    called_funcs: List[FunctionCallingRecord] = agent_response.info[
        'called_functions']
    for called_func in called_funcs:
        print(str(called_func))

    assert len(called_funcs) > 0
    assert str(called_funcs[0]).startswith("Function Execution")

    assert called_funcs[0].func_name == "mul"
    assert called_funcs[0].args == {"a": 2, "b": 8}
    assert called_funcs[0].result == 16
