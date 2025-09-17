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
from unittest.mock import MagicMock, PropertyMock, patch

import pytest


class TestVertexAIVeoToolkit:
    @pytest.fixture
    def mock_toolkit(self):
        r"""Create a mock VertexAIVeoToolkit for testing."""
        # Set required environment variables
        os.environ['GOOGLE_CLOUD_PROJECT'] = 'test-project'
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/fake/path/creds.json'

        # Mock the Google Cloud AI Platform API calls
        with (
            patch('google.cloud.aiplatform.init'),
            patch('google.cloud.aiplatform.gapic.PredictionServiceClient'),
        ):
            from camel.toolkits.vertex_ai_veo_toolkit import (
                VertexAIVeoToolkit,
            )

            toolkit = VertexAIVeoToolkit(
                project_id='test-project', location='us-central1'
            )

            yield toolkit

        # Clean up environment variables
        os.environ.pop('GOOGLE_CLOUD_PROJECT', None)
        os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)

    def test_toolkit_initialization(self, mock_toolkit):
        r"""Test that the toolkit initializes correctly."""
        assert mock_toolkit.project_id == 'test-project'
        assert mock_toolkit.location == 'us-central1'

    def test_get_tools(self, mock_toolkit):
        r"""Test that get_tools returns the expected function tools."""
        tools = mock_toolkit.get_tools()

        assert len(tools) == 3
        tool_names = [tool.get_function_name() for tool in tools]

        expected_tools = [
            'generate_video_from_text',
            'generate_video_from_image',
            'extend_video',
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_get_async_tools(self, mock_toolkit):
        r"""Test that get_async_tools returns expected async function tools."""
        async_tools = mock_toolkit.get_async_tools()

        assert len(async_tools) == 3
        tool_names = [tool.get_function_name() for tool in async_tools]

        expected_tools = [
            'agenerate_video_from_text',
            'agenerate_video_from_image',
            'aextend_video',
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @patch('builtins.open')
    @patch('base64.b64encode')
    def test_process_image_local_file(
        self, mock_b64encode, mock_open, mock_toolkit
    ):
        r"""Test image processing for local files."""
        # Mock file operations
        mock_open.return_value.__enter__.return_value.read.return_value = (
            b'fake_image_data'
        )
        mock_b64encode.return_value = b'encoded_data'

        # Test PNG file
        image_data, mime_type = mock_toolkit._process_image(
            '/path/to/image.png'
        )

        assert mime_type == 'image/png'
        assert image_data == 'encoded_data'

    @patch('builtins.open')
    def test_process_image_invalid_format(self, mock_open, mock_toolkit):
        r"""Test that invalid image formats raise an error."""
        # Mock file operations
        mock_open.return_value.__enter__.return_value.read.return_value = (
            b'fake_image_data'
        )

        with pytest.raises(ValueError, match="Unsupported image format"):
            mock_toolkit._process_image('/path/to/image.bmp')

    def test_parse_video_response_success(self, mock_toolkit):
        r"""Test parsing a successful video response."""
        # Mock a successful response
        mock_response = MagicMock()
        mock_response.predictions = [{'video_uri': 'gs://bucket/video.mp4'}]
        mock_response.metadata = {'generation_time': '30s'}

        result = mock_toolkit._parse_video_response(mock_response)

        assert result['success'] is True
        assert len(result['videos']) == 1
        assert 'metadata' in result

    def test_parse_video_response_error(self, mock_toolkit):
        r"""Test parsing a video response with error."""
        # Mock a response that raises an exception
        mock_response = MagicMock()
        mock_response.predictions = None

        # Make accessing predictions raise an exception
        type(mock_response).predictions = PropertyMock(
            side_effect=Exception("API Error")
        )

        result = mock_toolkit._parse_video_response(mock_response)

        assert result['success'] is False
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_async_methods_exist(self, mock_toolkit):
        r"""Test that async methods exist and are callable."""
        # Test that async methods exist
        assert hasattr(mock_toolkit, 'agenerate_video_from_text')
        assert hasattr(mock_toolkit, 'agenerate_video_from_image')
        assert hasattr(mock_toolkit, 'aextend_video')

        # Test that they are callable
        assert callable(mock_toolkit.agenerate_video_from_text)
        assert callable(mock_toolkit.agenerate_video_from_image)
        assert callable(mock_toolkit.aextend_video)


@pytest.mark.model_backend
class TestVertexAIVeoToolkitIntegration:
    r"""Integration tests that require actual API access."""

    @pytest.mark.skipif(
        not os.getenv('GOOGLE_CLOUD_PROJECT'),
        reason="Requires GOOGLE_CLOUD_PROJECT environment variable",
    )
    def test_real_toolkit_initialization(self):
        r"""Test initialization with real Google Cloud credentials."""
        from camel.toolkits.vertex_ai_veo_toolkit import VertexAIVeoToolkit

        toolkit = VertexAIVeoToolkit()
        assert toolkit.project_id is not None
        assert toolkit.location == 'us-central1'

    @pytest.mark.skipif(
        not os.getenv('GOOGLE_CLOUD_PROJECT'),
        reason="Requires GOOGLE_CLOUD_PROJECT environment variable",
    )
    @pytest.mark.very_slow
    def test_real_video_generation(self):
        r"""Test actual video generation (requires API access and billing)."""
        from camel.toolkits.vertex_ai_veo_toolkit import VertexAIVeoToolkit

        toolkit = VertexAIVeoToolkit()

        # This would make a real API call
        # result = toolkit.generate_video_from_text(
        #     text_prompt="A simple test video",
        #     duration=5
        # )
        #
        # assert 'success' in result

        # For now, just test that the method exists
        assert hasattr(toolkit, 'generate_video_from_text')


if __name__ == "__main__":
    pytest.main([__file__])
