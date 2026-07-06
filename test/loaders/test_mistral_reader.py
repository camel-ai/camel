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

import base64
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from camel.loaders.mistral_loader import MistralLoader


@pytest.mark.skipif(
    os.environ.get("MISTRAL_API_KEY") is None,
    reason="MISTRAL_API_KEY not available",
)
def test_init_with_env_variable():
    r"""Test MistralLoader initialization with environment variable."""
    with patch("mistralai.Mistral") as mock_mistral:
        loader = MistralLoader()
        mock_mistral.assert_called_once_with(
            api_key=os.environ.get("MISTRAL_API_KEY")
        )
        assert loader.model == "mistral-ocr-latest"


def test_init_with_api_key():
    r"""Test MistralLoader initialization with provided API key."""
    test_api_key = "test_api_key"
    test_model = "test-model"

    with patch("mistralai.Mistral") as mock_mistral:
        loader = MistralLoader(api_key=test_api_key, model=test_model)
        mock_mistral.assert_called_once_with(api_key=test_api_key)
        assert loader.model == test_model


def test_encode_file_success():
    r"""Test file encoding with a valid file."""
    loader = MistralLoader(api_key="dummy_key")

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(b"test content")
        temp_file_path = temp_file.name

    try:
        # Test encoding
        encoded = loader._encode_file(temp_file_path)
        assert encoded == base64.b64encode(b"test content").decode('utf-8')
    finally:
        # Clean up
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def test_encode_file_not_found():
    r"""Test file encoding with a non-existent file."""
    loader = MistralLoader(api_key="dummy_key")

    # Test with a non-existent file
    with patch("camel.loaders.mistral_loader.logger") as mock_logger:
        encoded = loader._encode_file("/non/existent/file.pdf")
        assert encoded == ""
        mock_logger.error.assert_called_once()


def test_load_single_local_file():
    r"""Test _load_single with a local file."""
    # Mock OCR response
    mock_ocr_response = MagicMock()

    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
        temp_file.write(b"test pdf content")
        temp_file_path = temp_file.name

    try:
        with patch("mistralai.Mistral") as mock_mistral_class:
            # Set up the mock chain
            mock_mistral = MagicMock()
            mock_mistral_class.return_value = mock_mistral
            mock_mistral.ocr = MagicMock()
            mock_mistral.ocr.process.return_value = mock_ocr_response

            # Create loader and test _load_single
            loader = MistralLoader(api_key="dummy_key")
            result = loader._load_single(temp_file_path)

            # Verify the result contains our mock response
            assert result["content"] == mock_ocr_response
            mock_mistral.ocr.process.assert_called_once()

            # Verify document_config was correctly constructed
            call_args = mock_mistral.ocr.process.call_args[1]
            assert call_args["model"] == "mistral-ocr-latest"
            assert call_args["document"]["type"] == "document_url"
            assert (
                "data:application/pdf;base64,"
                in call_args["document"]["document_url"]
            )
    finally:
        # Clean up
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def test_load_single_url():
    r"""Test _load_single with a URL."""
    # Mock OCR response
    mock_ocr_response = MagicMock()
    test_url = "https://example.com/document.pdf"

    with patch("mistralai.Mistral") as mock_mistral_class:
        # Set up the mock chain
        mock_mistral = MagicMock()
        mock_mistral_class.return_value = mock_mistral
        mock_mistral.ocr = MagicMock()
        mock_mistral.ocr.process.return_value = mock_ocr_response

        # Create loader and test _load_single with URL
        loader = MistralLoader(api_key="dummy_key")
        result = loader._load_single(test_url)

        # Verify the result
        assert result["content"] == mock_ocr_response
        mock_mistral.ocr.process.assert_called_once()

        # Verify document_config was correctly constructed
        call_args = mock_mistral.ocr.process.call_args[1]
        assert call_args["model"] == "mistral-ocr-latest"
        assert call_args["document"]["type"] == "document_url"
        assert call_args["document"]["document_url"] == test_url


def test_load_single_image():
    r"""Test _load_single with an image file."""
    # Mock OCR response
    mock_ocr_response = MagicMock()
    test_url = "https://example.com/image.jpg"

    with patch("mistralai.Mistral") as mock_mistral_class:
        # Set up the mock chain
        mock_mistral = MagicMock()
        mock_mistral_class.return_value = mock_mistral
        mock_mistral.ocr = MagicMock()
        mock_mistral.ocr.process.return_value = mock_ocr_response

        # Create loader and test _load_single with image URL
        loader = MistralLoader(api_key="dummy_key", is_image=True)
        result = loader._load_single(test_url)

        # Verify the result
        assert result["content"] == mock_ocr_response
        mock_mistral.ocr.process.assert_called_once()

        # Verify document_config was correctly constructed
        call_args = mock_mistral.ocr.process.call_args[1]
        assert call_args["model"] == "mistral-ocr-latest"
        assert call_args["document"]["type"] == "image_url"
        assert call_args["document"]["image_url"] == test_url
