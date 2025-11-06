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

import os
import sys
import tempfile
from unittest.mock import MagicMock

import pytest
import yaml

# Set up module mocks before any imports that might use them
sys.modules['bohrium'] = MagicMock()
sys.modules['bohrium._client'] = MagicMock()
sys.modules['bohrium.resources'] = MagicMock()
sys.modules['bohrium._client.Bohrium'] = MagicMock()
sys.modules['bohrium.resources.Job'] = MagicMock()

# Import after setting up mocks
from camel.toolkits import BohriumToolkit  # noqa: E402


@pytest.fixture
def mock_bohrium_client():
    """Create a mock for Bohrium client."""
    mock_client = MagicMock()
    mock_client.post.return_value.json.return_value = {
        "code": 0,
        "data": {"jobGroupId": 12345, "jobId": 67890, "bohrJobId": 54321},
    }
    mock_client.get.return_value.json.return_value = {
        "code": 0,
        "data": {
            "name": "test_job",
            "status": "PENDING",
            "createTime": "2023-01-01T00:00:00Z",
        },
    }
    return mock_client


@pytest.fixture
def mock_job(mock_bohrium_client):
    """Create a mock for Job class."""
    mock_job = MagicMock()
    mock_job.submit.return_value = {"jobId": 67890, "jobGroupId": 12345}
    mock_job.detail.return_value = {
        "name": "test_job",
        "status": "PENDING",
        "createTime": "2023-01-01T00:00:00Z",
    }
    return mock_job


@pytest.fixture
def sample_yaml_file():
    """Create a temporary YAML file for testing."""
    with tempfile.NamedTemporaryFile(
        suffix=".yaml", delete=False, mode='w'
    ) as temp_file:
        yaml_content = {
            "job_name": "test-bohrium-job",
            "machine_type": "c2_m4_cpu",
            "cmd": "mpirun -n 2 lmp_mpi -i in.shear",
            "image_address": "registry.dp.tech/dptech/lammps:29Sep2021",
        }
        yaml.dump(yaml_content, temp_file)
        temp_path = temp_file.name

    yield temp_path

    # Clean up the temporary file
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def mock_bohrium_class():
    """Create a mock for Bohrium class."""
    return MagicMock()


@pytest.fixture
def mock_job_class():
    """Create a mock for Job class."""
    return MagicMock()


def test_init(mock_job_class, mock_bohrium_class):
    """Test initialization of BohriumToolkit."""

    # Test initialization with all parameters
    toolkit = BohriumToolkit(
        api_key="test_api_key",
        project_id=123456,
        yaml_path="test_path.yaml",
        timeout=30.0,
        _test_mode=True,
    )

    # Check that the class attributes were set correctly
    assert toolkit._project_id == 123456
    assert toolkit._yaml_path == "test_path.yaml"

    # Check that custom_insert was set up
    assert hasattr(toolkit, '_custom_insert')


def test_submit_job_with_yaml(
    mock_job_class, mock_bohrium_class, sample_yaml_file
):
    """Test submitting a job using a YAML file."""
    # Setup mocks
    mock_job = mock_job_class.return_value

    # Setup mock return values
    mock_job.submit.return_value = {"jobId": 67890, "jobGroupId": 12345}

    # Initialize toolkit with project_id and yaml_path
    toolkit = BohriumToolkit(
        api_key="test_api_key",
        project_id=123456,
        yaml_path=sample_yaml_file,
        _test_mode=True,
    )

    toolkit._job = mock_job

    # Submit the job
    result = toolkit.submit_job()

    # Check that the job was submitted with the correct parameters
    mock_job.submit.assert_called_once()
    args, kwargs = mock_job.submit.call_args

    # Check that the parameters from the YAML file were used
    assert kwargs["job_name"] == "test-bohrium-job"
    assert kwargs["machine_type"] == "c2_m4_cpu"
    assert kwargs["cmd"] == "mpirun -n 2 lmp_mpi -i in.shear"
    assert (
        kwargs["image_address"] == "registry.dp.tech/dptech/lammps:29Sep2021"
    )
    assert (
        kwargs["project_id"] == 123456
    )  # This comes from the toolkit initialization

    # Check the result format
    assert "status" in result
    assert result["status"] == "Job submitted successfully"

    # Check if result contains the expected job information
    # The information might be in the "result" field as a nested structure
    if "result" in result and isinstance(result["result"], dict):
        assert "jobId" in result["result"]
        assert result["result"]["jobId"] == 67890
    else:
        raise AssertionError(f"Unexpected result structure: {result}")


def test_submit_job_missing_parameters(mock_job_class, mock_bohrium_class):
    """Test submitting a job with missing parameters."""
    # Setup mocks
    mock_job = mock_job_class.return_value

    # Initialize toolkit without yaml_path
    toolkit = BohriumToolkit(
        api_key="test_api_key", project_id=123456, _test_mode=True
    )

    # Set the method we're patching manually
    toolkit._job = mock_job

    # Submit the job with project_id but no yaml_path
    # Now that we have default parameters in submit_job,
    # it should not fail with missing parameters
    result = toolkit.submit_job()

    # Check the result contains success status
    assert "status" in result
    assert result["status"] == "Job submitted successfully"


def test_get_job_details(mock_job_class, mock_bohrium_class):
    """Test getting job details."""
    # Setup mocks
    mock_job = mock_job_class.return_value

    # Setup mock return values
    mock_job.detail.return_value = {
        "name": "test_job",
        "status": "PENDING",
        "createTime": "2023-01-01T00:00:00Z",
    }

    # Initialize toolkit
    toolkit = BohriumToolkit(
        api_key="test_api_key", project_id=123456, _test_mode=True
    )

    # Set the method we're patching manually
    toolkit._job = mock_job

    # Get job details
    result = toolkit.get_job_details(67890)

    # Check that the correct job details were returned
    mock_job.detail.assert_called_once_with(67890)
    assert result["name"] == "test_job"
    assert result["status"] == "PENDING"


def test_terminate_job(mock_job_class, mock_bohrium_class):
    """Test terminating a job."""
    # Setup mocks
    mock_job = mock_job_class.return_value

    # Initialize toolkit
    toolkit = BohriumToolkit(
        api_key="test_api_key", project_id=123456, _test_mode=True
    )

    # Set the method we're patching manually
    toolkit._job = mock_job

    # Terminate job
    result = toolkit.terminate_job(67890)

    # Check that the job was terminated
    mock_job.terminate.assert_called_once_with(67890)
    assert result["status"] == "Job terminated successfully"


def test_kill_job(mock_job_class, mock_bohrium_class):
    """Test killing a job."""
    # Setup mocks
    mock_job = mock_job_class.return_value

    # Initialize toolkit
    toolkit = BohriumToolkit(
        api_key="test_api_key", project_id=123456, _test_mode=True
    )

    # Set the method we're patching manually
    toolkit._job = mock_job

    # Kill job
    result = toolkit.kill_job(67890)

    # Check that the job was killed
    mock_job.kill.assert_called_once_with(67890)
    assert result["status"] == "Job killed successfully"


def test_get_job_logs(mock_job_class, mock_bohrium_class):
    """Test getting job logs."""
    # Setup mocks
    mock_job = mock_job_class.return_value
    mock_job.log.return_value = "Test log output"

    # Initialize toolkit
    toolkit = BohriumToolkit(
        api_key="test_api_key", project_id=123456, _test_mode=True
    )

    # Set the method we're patching manually
    toolkit._job = mock_job

    # Get job logs
    result = toolkit.get_job_logs(67890)

    # Check that the logs were retrieved
    mock_job.log.assert_called_once_with(
        67890, log_file="STDOUTERR", page=-1, page_size=8192
    )
    assert result == "Test log output"


def test_create_job_group(mock_job_class, mock_bohrium_class):
    """Test creating a job group."""
    # Setup mocks
    mock_job = mock_job_class.return_value

    # Initialize toolkit
    toolkit = BohriumToolkit(
        api_key="test_api_key", project_id=123456, _test_mode=True
    )

    # Set the method we're patching manually
    toolkit._job = mock_job

    # Create job group
    result = toolkit.create_job_group(123456, "test-group")

    # Check that the job group was created
    mock_job.create_job_group.assert_called_once_with(123456, "test-group")
    assert result["status"] == "Job group created successfully"


def test_download_job_results(mock_job_class, mock_bohrium_class):
    """Test downloading job results."""
    # Setup mocks
    mock_job = mock_job_class.return_value

    # Initialize toolkit
    toolkit = BohriumToolkit(
        api_key="test_api_key", project_id=123456, _test_mode=True
    )

    # Set the method we're patching manually
    toolkit._job = mock_job

    # Download job results
    result = toolkit.download_job_results(67890, "/tmp/results")

    # Check that the results were downloaded
    mock_job.download.assert_called_once_with(67890, "/tmp/results")
    assert result["status"] == "Job results downloaded successfully"
    assert result["path"] == "/tmp/results"


def test_get_tools(mock_job_class, mock_bohrium_class):
    """Test getting available tools."""
    # Initialize toolkit

    # Initialize toolkit
    toolkit = BohriumToolkit(
        api_key="test_api_key", project_id=123456, _test_mode=True
    )

    # Get tools
    tools = toolkit.get_tools()

    # Check that we have the expected number of tools
    assert (
        len(tools) == 7
    )  # Should have 7 tools based on the current implementation

    # Check that all tools are FunctionTool instances
    from camel.toolkits.function_tool import FunctionTool

    for tool in tools:
        assert isinstance(tool, FunctionTool)

    # Check that all expected tool functions are included
    tool_names = [tool.get_function_name() for tool in tools]
    expected_names = [
        "submit_job",
        "get_job_details",
        "terminate_job",
        "kill_job",
        "get_job_logs",
        "create_job_group",
        "download_job_results",
    ]
    for name in expected_names:
        assert name in tool_names
