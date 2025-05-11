import pytest
from camel.types import ModelType
from camel.models import DeepSeekModel
from camel.agents.paper_to_code_agent import PaperToCodeAgent


@pytest.mark.model_backend
def test_gen_code():
    # api_key = ""
    # model = DeepSeekModel(model_type=ModelType.DEEPSEEK_CHAT, api_key=api_key)

    import os
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent
    test_file_path = os.path.join(project_root, "test/agents/Transformer.json")

    agent = PaperToCodeAgent(
        file_path=test_file_path,
        paper_name="transformer",
        paper_format="JSON",
        # model=model,
    )
    agent.step("please help me implement transformer")


if __name__ == "__main__":
    test_gen_code()
