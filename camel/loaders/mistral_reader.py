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
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from mistralai.models import OCRResponse

from camel.logger import get_logger
from camel.utils import api_keys_required

logger = get_logger(__name__)


class MistralReader:
    r"""Mistral Document Loader."""

    @api_keys_required(
        [
            ("api_key", "MISTRAL_API_KEY"),
        ]
    )
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = "mistral-ocr-latest",
    ) -> None:
        r"""Initialize the MistralReader.

        Args:
            api_key (Optional[str]): The API key for the Mistral API.
                (default: :obj:`None`)
            model (Optional[str]): The model to use for OCR.
                (default: :obj:`"mistral-ocr-latest"`)
        """
        from mistralai import Mistral

        self._api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        self.client = Mistral(api_key=self._api_key)
        self.model = model

    def _encode_file(self, file_path: str) -> str:
        r"""Encode the pdf to base64.

        Args:
            file_path (str): Path to the input file.

        Returns:
            str: base64 version of the file.
        """

        import base64

        try:
            with open(file_path, "rb") as pdf_file:
                return base64.b64encode(pdf_file.read()).decode('utf-8')
        except FileNotFoundError:
            logger.error(f"Error: The file {file_path} was not found.")
            return ""
        except Exception as e:
            logger.error(f"Error: {e}")
            return ""

    def extract_text(
        self,
        file_path: str,
        is_image: bool = False,
        pages: Optional[List[int]] = None,
        include_image_base64: Optional[bool] = None,
    ) -> "OCRResponse":
        r"""Converts the given file to Markdown format.

        Args:
            file_path (str): Path to the input file or a remote URL.
            is_image (bool): Whether the file or URL is an image. If True,
                uses image_url type instead of document_url.
                (default: :obj:`False`)
            pages (Optional[List[int]]): Specific pages user wants to process
                in various formats: single number, range, or list of both.
                Starts from 0. (default: :obj:`None`)
            include_image_base64 (Optional[bool]): Whether to include image
                URLs in response. (default: :obj:`None`)

        Returns:
            OCRResponse: page wise extractions.

        Raises:
            FileNotFoundError: If the specified local file does not exist.
            ValueError: If the file format is not supported.
            Exception: For other errors during conversion.
        """
        # Check if the input is a URL (starts with http:// or https://)
        is_url = file_path.startswith(('http://', 'https://'))

        if not is_url and not os.path.isfile(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        try:
            if is_url:
                logger.info(f"Processing URL: {file_path}")
                if is_image:
                    document_config = {
                        "type": "image_url",
                        "image_url": file_path,
                    }
                else:
                    document_config = {
                        "type": "document_url",
                        "document_url": file_path,
                    }
            else:
                logger.info(f"Converting local file: {file_path}")
                base64_file = self._encode_file(file_path)
                if is_image:
                    document_config = {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{base64_file}",
                    }
                else:
                    document_config = {
                        "type": "document_url",
                        "document_url": f"data:application/"
                        f"pdf;base64,{base64_file}",
                    }

            ocr_response = self.client.ocr.process(
                model=self.model,
                document=document_config,  # type: ignore[arg-type]
                pages=None if is_image else pages,
                include_image_base64=include_image_base64,
            )

            logger.info(f"Processing completed successfully for: {file_path}")
            return ocr_response
        except Exception as e:
            logger.error(f"Error processing '{file_path}': {e}")
            raise ValueError(f"Error processing '{file_path}': {e}")
