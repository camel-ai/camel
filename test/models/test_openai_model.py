import pytest
from camel.models import OpenAIModel
from camel.typing import ModelType
from camel.configs import ChatGPTConfig


@pytest.mark.model_backend
@pytest.mark.parametrize("model_type", [
    ModelType.GPT_3_5_TURBO,
    ModelType.GPT_3_5_TURBO_16K,
    ModelType.GPT_4,
])
def test_openai_model(model_type):
    model_config_dict = ChatGPTConfig().__dict__
    model = OpenAIModel(model_type, model_config_dict)

    messages = [
        {
            "role": "system",
            "content": "Initialize system",
        },
        {
            "role": "user",
            "content": "Hello",
        },
    ]

    response = model.run(messages)
    assert isinstance(response, dict)
    assert "choices" in response
    assert isinstance(response["choices"], list)
    assert len(response["choices"]) > 0
    assert isinstance(response["choices"][0], dict)
    assert "message" in response["choices"][0]
    assert isinstance(response["choices"][0]["message"], dict)
    assert "role" in response["choices"][0]["message"]
    assert response["choices"][0]["message"]["role"] == "assistant"
