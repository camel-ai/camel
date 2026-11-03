# test_paper_to_code_agent.py

import json
import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from camel.agents import PaperToCodeAgent

# Import Pydantic models from the agent file to construct mock responses
from camel.agents.paper_to_code_agent import (
    PaperToCodeConfig,
    PaperToCodeDesign,
    PaperToCodeImplementation,
    PaperToCodeLogicAnalysis,
    PaperToCodeOverview,
    PaperToCodeTasks,
    YamlFile,
)
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


def create_mock_completion(pydantic_model_instance):
    """Creates a mock completion object that mimics the agent's step response."""
    mock_response = MagicMock()
    # The agent uses model_dump_json() to serialize the Pydantic model
    # Ensure aliases are used for consistency with how the agent expects to parse JSON
    mock_response.model_dump_json.return_value = pydantic_model_instance.model_dump_json(
        by_alias=True)
    # The agent accesses the raw content string from the message object
    # This content MUST be serialized with by_alias=True for the agent's internal parsing
    mock_response.msg = BaseMessage(
        role_name="assistant",
        role_type="assistant",
        meta_dict=None,
        content=pydantic_model_instance.model_dump_json(by_alias=True),
    )
    # The coding phase also needs the msgs attribute
    mock_response.msgs = [mock_response.msg]
    return mock_response


@pytest.fixture
def mock_paper_dir(tmp_path):
    """Creates a temporary directory for paper and output files."""
    paper_name = "TestPaper"
    # The agent creates these directories in its __init__
    os.makedirs(tmp_path / paper_name / "output", exist_ok=True)
    os.makedirs(tmp_path / paper_name / "repo", exist_ok=True)
    return tmp_path, paper_name


@pytest.fixture
def mock_paper_file(mock_paper_dir):
    """Creates a dummy JSON paper file."""
    tmp_path, paper_name = mock_paper_dir
    paper_path = tmp_path / f"{paper_name}.json"
    paper_content = {
        "paper_id": "1234.5678",
        "title": "Mock Paper for Testing",
        "authors": [{
            "name": "Dr. Mock"
        }],
        "abstract": "This is a mock paper.",
        "body_text": [{
            "text": "The core method is to add 1 and 1."
        }],
        "bib_entries": {},
        "ref_spans": [],
        "cite_spans": [],
    }
    with open(paper_path, 'w') as f:
        json.dump(paper_content, f)
    return paper_path


@pytest.fixture
def agent(mock_paper_file, mock_paper_dir):
    """Initializes the PaperToCodeAgent with a stub model."""
    tmp_path, paper_name = mock_paper_dir
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.STUB,
    )
    # The agent's logic relies on its own path construction, so we point it to tmp_path
    # by ensuring the paper file path is within it.
    agent_instance = PaperToCodeAgent(
        file_path=str(mock_paper_file),
        paper_name=paper_name,
        paper_format='JSON',
        model=model,
    )

    # Redirect agent's output paths to be inside the test's temporary directory
    # agent.output_path is originally paper_name/output relative to CWD
    # agent.output_repo_path is originally paper_name/repo relative to CWD
    agent_instance.output_path = str(tmp_path / "output")
    agent_instance.output_repo_path = str(tmp_path / "repo")
    os.makedirs(agent_instance.output_path, exist_ok=True)
    os.makedirs(agent_instance.output_repo_path, exist_ok=True)
    return agent_instance


def test_process_removes_spans(agent, mock_paper_file):
    """Tests the JSON cleaning functionality of the _process method."""
    with open(mock_paper_file, 'r') as f:
        original_data = json.load(f)
    print(original_data)
    assert "authors" in original_data

    agent._process()

    with open(mock_paper_file, 'r') as f:
        processed_data = json.load(f)
    print(processed_data)
    assert "authors" not in processed_data


# ruff: noqa: E501
@patch('camel.agents.chat_agent.ChatAgent.step')
def test_full_workflow(mock_chat_agent_step, agent, mock_paper_dir):
    # Set logger level to INFO to catch potential warnings
    logging.getLogger("camel.agents.paper_to_code_agent").setLevel(logging.INFO)
    """Tests the full paper-to-code workflow with mocked LLM responses."""
    tmp_path, paper_name = mock_paper_dir

    # 1. Define Mock LLM Responses for each step
    # Planning Phase (4 steps)
    mock_overview = PaperToCodeOverview(
        content="This is the implementation plan.")
    mock_design = PaperToCodeDesign(
        implementation_approach="Use PyTorch.",
        file_list=["main.py", "utils.py"],
        data_structures_and_interfaces="classDiagram\nclass Main{}",
        program_call_flow="sequenceDiagram\nMain->>Utils: call()",
        unclear_aspects="None",
    )
    mock_tasks = PaperToCodeTasks(
        required_packages=["torch==2.0.0"],
        required_other_packages=["No third-party dependencies required"],
        logic_analysis=[
            ["utils.py", "Utility functions."],
            ["main.py", "Main execution script."],
        ],
        task_list=["config.yaml", "utils.py", "main.py"],
        full_api_spec="",
        shared_knowledge="N/A",
        unclear_aspects="N/A",
    )
    mock_config = PaperToCodeConfig(yaml_files=[
        YamlFile(filename="config.yaml", content="learning_rate: 0.001")
    ])

    # Analyzing Phase (2 steps, for utils.py and main.py)
    mock_analysis_utils = PaperToCodeLogicAnalysis(
        content=
        "### Analysis for utils.py\n\n#### Overview\nThis is an overview.\n\n#### Key Components\n- A helper function."
    )
    mock_analysis_main = PaperToCodeLogicAnalysis(
        content=
        "### Analysis for main.py\n\n#### Overview\nThis is an overview.\n\n#### Key Components\n- Main script logic."
    )

    # Coding Phase (2 steps)
    mock_code_utils = PaperToCodeImplementation(
        content="```python\n# utils.py\ndef helper():\n    return 'Hello'\n```")
    mock_code_main = PaperToCodeImplementation(
        content=
        "```python\n# main.py\nimport utils\n\nif __name__ == '__main__':\n    print(utils.helper())\n```"
    )

    # Set up the mock for ChatAgent.step to return responses in the correct order
    mock_chat_agent_step.side_effect = [
        create_mock_completion(mock_overview),
        create_mock_completion(mock_design),
        create_mock_completion(mock_tasks),
        create_mock_completion(mock_config),
        create_mock_completion(mock_analysis_utils),
        create_mock_completion(mock_analysis_main),
        create_mock_completion(mock_code_utils),
        create_mock_completion(mock_code_main),
    ]

    # 2. Run the agent's main step method
    # In the agent's code, `step` calls the private methods `_process`, `_planning`, etc.
    # We will call these private methods sequentially to test the whole flow.
    agent._process()
    agent._planning()
    agent._extract_config()  # This uses the files created by _planning
    agent._analyzing()
    agent._coding()

    # 3. Assertions
    # Check that the mock was called the right number of times
    # 4 (planning) + 2 (analyzing) + 2 (coding) = 8
    assert mock_chat_agent_step.call_count == 8

    # Check planning artifacts
    planning_response_path = os.path.join(agent.output_path,
                                          'planning_response.json')
    config_path = os.path.join(agent.output_path, 'planning_config.yaml')
    assert os.path.exists(planning_response_path)
    assert os.path.exists(config_path)

    # Check analyzing artifacts
    analysis_artifact_path = os.path.join(agent.output_path,
                                          'analyzing_artifacts',
                                          'utils.py_simple_analysis.txt')
    assert os.path.exists(analysis_artifact_path)
    with open(analysis_artifact_path, 'r') as f:
        assert "Analysis for utils.py" in f.read()

    # Check coding artifacts (the final repository)
    repo_utils_path = os.path.join(agent.output_repo_path, 'utils.py')
    repo_main_path = os.path.join(agent.output_repo_path, 'main.py')
    assert os.path.exists(repo_utils_path)
    assert os.path.exists(repo_main_path)

    with open(repo_utils_path, 'r') as f:
        content = f.read()
        assert "def helper():" in content
        assert "return 'Hello'" in content

    with open(repo_main_path, 'r') as f:
        content = f.read()
        assert "import utils" in content
        assert "print(utils.helper())" in content
