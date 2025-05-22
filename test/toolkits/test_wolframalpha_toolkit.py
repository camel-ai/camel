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
from unittest.mock import MagicMock, Mock, patch

from camel.toolkits import WolframAlphaToolkit


@patch('requests.get')
@patch('wolframalpha.Client')
@patch('os.environ.get')
def test_query_wolfram_alpha(mock_get_env, mock_client, mock_requests_get):
    mock_get_env.return_value = 'FAKE_APP_ID'

    mock_res = MagicMock()
    mock_res.get.side_effect = lambda key, default: {
        '@inputstring': 'calculate limit of sinx^2/x',
        'pod': [
            {
                '@title': 'Limit',
                'subpod': {'plaintext': 'lim_(x->0) (sin^2(x))/x = 0'},
                '@primary': 'true',
            },
            {
                '@title': 'Plot',
                'subpod': {'plaintext': None},
            },
        ],
    }[key]

    mock_instance = MagicMock()
    mock_instance.query.return_value = mock_res
    mock_client.return_value = mock_instance

    result = WolframAlphaToolkit().query_wolfram_alpha(
        "calculate limit of sinx^2/x"
    )

    expected_output = "lim_(x->0) (sin^2(x))/x = 0"

    assert result == expected_output


@patch('requests.get')
@patch('wolframalpha.Client')
@patch('os.environ.get')
def test_query_wolfram_alpha_step_by_step(
    mock_get_env, mock_client, mock_requests_get
):
    mock_get_env.return_value = 'FAKE_APP_ID'

    mock_res = MagicMock()
    mock_res.get.side_effect = lambda key, default: {
        '@inputstring': 'calculate limit of sinx^2/x',
        'pod': [
            {
                '@title': 'Limit',
                'subpod': {'plaintext': 'lim_(x->0) (sin^2(x))/x = 0'},
                '@primary': 'true',
            },
            {
                '@title': 'Plot',
                'subpod': {'plaintext': None},
            },
        ],
    }[key]

    mock_instance = MagicMock()
    mock_instance.query.return_value = mock_res
    mock_client.return_value = mock_instance

    mock_requests_get.return_value = MagicMock(status_code=200)
    mock_requests_get.return_value.text = """
    <queryresult success="true" error="false">
        <pod title="Results">
            <subpod>
                <stepbystepcontenttype>SBSStep</stepbystepcontenttype>
                <plaintext>lim_(x->0) (sin^2(x))/x = 0</plaintext>
            </subpod>
        </pod>
        <pod title="Plot">
            <subpod>
                <plaintext></plaintext>
            </subpod>
        </pod>
    </queryresult>
    """

    result = WolframAlphaToolkit().query_wolfram_alpha_step_by_step(
        "calculate limit of sinx^2/x"
    )

    expected_output = {
        "query": "calculate limit of sinx^2/x",
        "pod_info": [
            {
                "title": "Limit",
                "description": "lim_(x->0) (sin^2(x))/x = 0",
                "image_url": '',
            },
            {
                "title": "Plot",
                "description": None,
                "image_url": '',
            },
        ],
        "final_answer": "lim_(x->0) (sin^2(x))/x = 0",
        "steps": {"step1": "lim_(x->0) (sin^2(x))/x = 0"},
    }

    assert result == expected_output


def test_parse_wolfram_result():
    sample_wolfram_result = {
        "@inputstring": "What is 2+2?",
        "pod": [
            {
                "@title": "Input",
                "subpod": {
                    "plaintext": "2 + 2",
                    "img": {"@src": "http://example.com/image1.png"},
                },
            },
            {
                "@title": "Result",
                "subpod": {
                    "plaintext": "4",
                    "img": {"@src": "http://example.com/image2.png"},
                },
                "@primary": "true",
            },
        ],
    }
    expected_output = {
        "query": "What is 2+2?",
        "pod_info": [
            {
                "title": "Input",
                "description": "2 + 2",
                "image_url": "http://example.com/image1.png",
            },
            {
                "title": "Result",
                "description": "4",
                "image_url": "http://example.com/image2.png",
            },
        ],
        "final_answer": "4",
    }

    result = WolframAlphaToolkit()._parse_wolfram_result(sample_wolfram_result)

    assert (
        result == expected_output
    ), f"Expected {expected_output}, but got {result}"


@patch('requests.get')
def test_get_wolframalpha_step_by_step_solution(mock_get):
    sample_response = """
    <queryresult>
        <pod title="Results">
            <subpod>
                <stepbystepcontenttype>SBSHintStep</stepbystepcontenttype>
                <plaintext>Hint: | Step 1</plaintext>
            </subpod>
            <subpod>
                <stepbystepcontenttype>SBSHintStep</stepbystepcontenttype>
                <plaintext>Hint: | Step 2</plaintext>
            </subpod>
        </pod>
    </queryresult>
    """

    mock_get.return_value = Mock(text=sample_response)

    expected_steps = {"step1": "Step 1", "step2": "Step 2"}

    result = WolframAlphaToolkit()._get_wolframalpha_step_by_step_solution(
        "dummy_app_id", "dummy_query"
    )

    assert (
        result == expected_steps
    ), f"Expected {expected_steps}, but got {result}"
