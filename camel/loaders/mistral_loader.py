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
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    pass

from camel.loaders.base_loader import BaseLoader
from camel.logger import get_logger
from camel.utils import api_keys_required

logger = get_logger(__name__)


class MistralLoader(BaseLoader):
    r"""Mistral Document Loader adhering to the unified BaseLoader interface."""  # noqa: E501

    @api_keys_required([("api_key", "MISTRAL_API_KEY")])
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        model: str = "mistral-ocr-latest",
        is_image: bool = False,
        pages: Optional[List[int]] = None,
        include_image_base64: Optional[bool] = None,
        **kwargs: Any,
    ) -> None:
        if config:
            api_key = config.get('api_key', api_key)
            model = config.get('model', model)
            self.is_image = config.get('is_image', is_image)
            self.pages = config.get('pages', pages)
            self.include_image_base64 = config.get(
                'include_image_base64', include_image_base64
            )
        else:
            self.is_image = is_image
            self.pages = pages
            self.include_image_base64 = include_image_base64

        super().__init__(config=config)

        from mistralai import Mistral

        self._api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        self.client = Mistral(api_key=self._api_key)
        self.model = model

    @property
    def supported_formats(self) -> set[str]:
        return {"pdf", "jpg", "jpeg", "png", "url", "http", "https"}

    def _encode_file(self, file_path: str) -> str:
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

    def _load_single(
        self, source: str | Path, **kwargs: Any
    ) -> dict[str, Any]:
        file_path = str(source)
        is_url = file_path.startswith(('http://', 'https://'))

        if not is_url and not os.path.isfile(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            if is_url:
                logger.info(f"Processing URL: {file_path}")
                document_config = {
                    "type": "image_url" if self.is_image else "document_url",
                    "image_url"
                    if self.is_image
                    else "document_url": file_path,
                }
            else:
                logger.info(f"Converting local file: {file_path}")
                base64_file = self._encode_file(file_path)
                document_config = {
                    "type": "image_url" if self.is_image else "document_url",
                    "image_url" if self.is_image else "document_url": (
                        f"data:image/jpeg;base64,{base64_file}"
                        if self.is_image
                        else f"data:application/pdf;base64,{base64_file}"
                    ),
                }

            ocr_response = self.client.ocr.process(
                model=self.model,
                document=document_config,
                pages=None if self.is_image else self.pages,
                include_image_base64=self.include_image_base64,
            )

            logger.info(f"Processing completed successfully for: {file_path}")
            # BaseLoader expects a dict with content and source
            return {"content": ocr_response, "source": file_path}

        except Exception as e:
            logger.error(f"Error processing '{file_path}': {e}")
            raise ValueError(f"Error processing '{file_path}': {e}")
