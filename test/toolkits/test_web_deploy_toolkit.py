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
import shutil
import tempfile
from unittest.mock import Mock, patch

import pytest

from camel.toolkits import WebDeployToolkit


@pytest.fixture
def web_deploy_toolkit():
    r"""Create a WebDeployToolkit instance for testing."""
    return WebDeployToolkit()


@pytest.fixture
def temp_dir():
    r"""Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def test_initialization():
    r"""Test the initialization of WebDeployToolkit with default parameters."""
    toolkit = WebDeployToolkit()
    
    assert toolkit.timeout is None
    assert toolkit.add_branding_tag is True
    assert toolkit.logo_path == "../../misc/favicon.png"
    assert toolkit.tag_text == "Created by CAMEL"
    assert toolkit.tag_url == "https://github.com/camel-ai/camel"
    assert toolkit.remote_server_ip is None
    assert toolkit.remote_server_port == 8080
    assert toolkit.server_instances == {}


def test_initialization_with_custom_parameters():
    r"""Test the initialization of WebDeployToolkit with custom parameters."""
    toolkit = WebDeployToolkit(
        timeout=30.0,
        add_branding_tag=False,
        logo_path="custom_logo.png",
        tag_text="Custom Tag",
        tag_url="https://custom.com",
        remote_server_ip="192.168.1.100",
        remote_server_port=9000,
    )
    
    assert toolkit.timeout == 30.0
    assert toolkit.add_branding_tag is False
    assert toolkit.logo_path == "custom_logo.png"
    assert toolkit.tag_text == "Custom Tag"
    assert toolkit.tag_url == "https://custom.com"
    assert toolkit.remote_server_ip == "192.168.1.100"
    assert toolkit.remote_server_port == 9000


def test_build_custom_url(web_deploy_toolkit):
    r"""Test the _build_custom_url helper method."""
    # Test without subdirectory
    url = web_deploy_toolkit._build_custom_url("example.com")
    assert url == "http://example.com:8080"
    
    # Test with subdirectory
    url = web_deploy_toolkit._build_custom_url("example.com", "user123")
    assert url == "http://example.com:8080/user123"


def test_get_default_logo(web_deploy_toolkit):
    r"""Test the _get_default_logo method."""
    logo = web_deploy_toolkit._get_default_logo()
    assert logo.startswith("data:image/svg+xml,")
    assert "AI" in logo


def test_load_logo_as_data_uri_file_not_found(web_deploy_toolkit):
    r"""Test loading logo when file doesn't exist."""
    with patch.object(web_deploy_toolkit, '_get_default_logo', return_value="default_logo"):
        result = web_deploy_toolkit._load_logo_as_data_uri("nonexistent.png")
        assert result == "default_logo"


def test_load_logo_as_data_uri_with_valid_file(web_deploy_toolkit, temp_dir):
    r"""Test loading logo with a valid file."""
    # Create a simple SVG file
    svg_content = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="32" height="32" fill="red"/></svg>'
    svg_path = os.path.join(temp_dir, "test_logo.svg")
    with open(svg_path, 'w') as f:
        f.write(svg_content)
    
    result = web_deploy_toolkit._load_logo_as_data_uri(svg_path)
    assert result.startswith("data:image/svg+xml;base64,")


def test_inject_eigent_tag_with_body(web_deploy_toolkit):
    r"""Test injecting branding tag into HTML with body tag."""
    html_content = "<html><body><h1>Test</h1></body></html>"
    result = web_deploy_toolkit._inject_eigent_tag(html_content)
    
    assert "<h1>Test</h1>" in result
    assert "eigent-floating-ball" in result
    assert result.count("</body>") == 1


def test_inject_eigent_tag_without_body(web_deploy_toolkit):
    r"""Test injecting branding tag into HTML without body tag."""
    html_content = "<h1>Test</h1>"
    result = web_deploy_toolkit._inject_eigent_tag(html_content)
    
    assert "<h1>Test</h1>" in result
    assert "eigent-floating-ball" in result


def test_inject_eigent_tag_disabled(web_deploy_toolkit):
    r"""Test that branding tag is not injected when disabled."""
    web_deploy_toolkit.add_branding_tag = False
    html_content = "<html><body><h1>Test</h1></body></html>"
    result = web_deploy_toolkit._inject_eigent_tag(html_content)
    
    assert result == html_content
    assert "eigent-floating-ball" not in result


@patch('subprocess.run')
def test_init_react_project_success(mock_run, web_deploy_toolkit, temp_dir):
    r"""Test successful React project initialization."""
    mock_run.return_value = Mock(returncode=0, stderr="")
    
    with patch('os.path.exists', return_value=False):
        result = web_deploy_toolkit.init_react_project(
            "test-project", 
            directory=temp_dir
        )
    
    assert result['success'] is True
    assert 'test-project' in result['project_name']
    assert 'created successfully' in result['message']


@patch('subprocess.run')
def test_init_react_project_already_exists(mock_run, web_deploy_toolkit, temp_dir):
    r"""Test React project initialization when directory already exists."""
    project_path = os.path.join(temp_dir, "existing-project")
    os.makedirs(project_path)
    
    result = web_deploy_toolkit.init_react_project(
        "existing-project", 
        directory=temp_dir
    )
    
    assert result['success'] is False
    assert 'already exists' in result['error']


@patch('subprocess.run')
def test_build_react_project_success(mock_run, web_deploy_toolkit, temp_dir):
    r"""Test successful React project build."""
    # Create a mock React project structure
    project_path = os.path.join(temp_dir, "test-project")
    os.makedirs(project_path)
    
    # Create package.json
    package_json = os.path.join(project_path, "package.json")
    with open(package_json, 'w') as f:
        f.write('{"name": "test-project"}')
    
    # Create node_modules directory
    node_modules = os.path.join(project_path, "node_modules")
    os.makedirs(node_modules)
    
    # Create build directory
    build_dir = os.path.join(project_path, "build")
    os.makedirs(build_dir)
    
    mock_run.return_value = Mock(returncode=0, stderr="")
    
    result = web_deploy_toolkit.build_react_project(project_path)
    
    assert result['success'] is True
    assert result['build_path'] == build_dir
    assert 'built successfully' in result['message']


def test_build_react_project_not_found(web_deploy_toolkit):
    r"""Test building React project when directory doesn't exist."""
    result = web_deploy_toolkit.build_react_project("/nonexistent/path")
    
    assert result['success'] is False
    assert 'does not exist' in result['error']


def test_build_react_project_no_package_json(web_deploy_toolkit, temp_dir):
    r"""Test building React project without package.json."""
    result = web_deploy_toolkit.build_react_project(temp_dir)
    
    assert result['success'] is False
    assert 'package.json not found' in result['error']


@patch('subprocess.Popen')
def test_serve_static_files_success(mock_popen, web_deploy_toolkit, temp_dir):
    r"""Test successful static file serving."""
    mock_process = Mock()
    mock_popen.return_value = mock_process
    
    with patch('time.sleep'):
        result = web_deploy_toolkit._serve_static_files(temp_dir, 8000)
    
    assert result['success'] is True
    assert result['port'] == 8000
    assert result['server_url'] == "http://localhost:8000"
    assert 8000 in web_deploy_toolkit.server_instances


def test_serve_static_files_directory_not_found(web_deploy_toolkit):
    r"""Test serving static files when directory doesn't exist."""
    result = web_deploy_toolkit._serve_static_files("/nonexistent", 8000)
    
    assert result['success'] is False
    assert 'does not exist' in result['error']


def test_serve_static_files_port_in_use(web_deploy_toolkit, temp_dir):
    r"""Test serving static files when port is already in use."""
    # Simulate port already in use
    web_deploy_toolkit.server_instances[8000] = Mock()
    
    result = web_deploy_toolkit._serve_static_files(temp_dir, 8000)
    
    assert result['success'] is False
    assert 'already in use' in result['error']


def test_deploy_html_content_local(web_deploy_toolkit):
    r"""Test deploying HTML content locally."""
    html_content = "<html><body><h1>Test</h1></body></html>"
    
    with patch.object(web_deploy_toolkit, '_deploy_to_local_server') as mock_deploy:
        mock_deploy.return_value = {'success': True}
        result = web_deploy_toolkit.deploy_html_content(html_content)
    
    assert result['success'] is True
    mock_deploy.assert_called_once()


def test_deploy_html_content_remote(web_deploy_toolkit):
    r"""Test deploying HTML content to remote server."""
    web_deploy_toolkit.remote_server_ip = "192.168.1.100"
    html_content = "<html><body><h1>Test</h1></body></html>"
    
    with patch.object(web_deploy_toolkit, '_deploy_to_remote_server') as mock_deploy:
        mock_deploy.return_value = {'success': True}
        result = web_deploy_toolkit.deploy_html_content(html_content)
    
    assert result['success'] is True
    mock_deploy.assert_called_once()


def test_stop_server_success(web_deploy_toolkit):
    r"""Test successfully stopping a server."""
    mock_process = Mock()
    web_deploy_toolkit.server_instances[8000] = mock_process
    
    result = web_deploy_toolkit.stop_server(8000)
    
    assert result['success'] is True
    assert result['port'] == 8000
    assert 8000 not in web_deploy_toolkit.server_instances
    mock_process.terminate.assert_called_once()


def test_stop_server_not_found(web_deploy_toolkit):
    r"""Test stopping a server that doesn't exist."""
    result = web_deploy_toolkit.stop_server(8000)
    
    assert result['success'] is False
    assert 'No server running' in result['error']


def test_deploy_folder_success(web_deploy_toolkit, temp_dir):
    r"""Test deploying a folder successfully."""
    # Create a test folder with an HTML file
    test_folder = os.path.join(temp_dir, "test_site")
    os.makedirs(test_folder)
    
    html_file = os.path.join(test_folder, "index.html")
    with open(html_file, 'w') as f:
        f.write("<html><body><h1>Test Site</h1></body></html>")
    
    with patch.object(web_deploy_toolkit, '_serve_static_files') as mock_serve:
        mock_serve.return_value = {
            'success': True,
            'server_url': 'http://localhost:8000'
        }
        result = web_deploy_toolkit.deploy_folder(test_folder)
    
    assert result['success'] is True
    mock_serve.assert_called_once()


def test_deploy_folder_not_found(web_deploy_toolkit):
    r"""Test deploying a folder that doesn't exist."""
    result = web_deploy_toolkit.deploy_folder("/nonexistent/folder")
    
    assert result['success'] is False
    assert 'does not exist' in result['error']


def test_deploy_folder_not_directory(web_deploy_toolkit, temp_dir):
    r"""Test deploying a path that is not a directory."""
    file_path = os.path.join(temp_dir, "not_a_directory.txt")
    with open(file_path, 'w') as f:
        f.write("test")
    
    result = web_deploy_toolkit.deploy_folder(file_path)
    
    assert result['success'] is False
    assert 'is not a directory' in result['error']


def test_get_tools(web_deploy_toolkit):
    r"""Test that get_tools returns the correct function tools."""
    tools = web_deploy_toolkit.get_tools()
    
    # Check that we have the expected number of tools
    assert len(tools) == 5
    
    # Check that the tools have the correct function names
    tool_names = [tool.get_function_name() for tool in tools]
    expected_names = [
        'init_react_project',
        'build_react_project',
        'deploy_html_content',
        'deploy_folder',
        'stop_server'
    ]
    
    for expected_name in expected_names:
        assert expected_name in tool_names