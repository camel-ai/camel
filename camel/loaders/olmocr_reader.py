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

import importlib
import os
import subprocess
import sys
from typing import Any, Dict, Optional, Set

from .base_loader import BaseLoader


class olmOCRLoader(BaseLoader):
    def __init__(self, config: Optional[Dict[str, Any]]) -> None:
        r"""olmOCR is an advanced process toolkit for PDF processing.

        Args:
            config (Optional[Dict[str, Any]]): Configuration for processing.
        """
        super().__init__(config)
        self.config = config if config else {}

        # Ensure olmOCR dependencies are installed
        self._ensure_dependencies()

    def _ensure_dependencies(self):
        r"""Checks and installs missing dependencies required by olmOCR."""
        required_packages = [
            "cached-path",
            "smart_open",
            "pypdf>=5.2.0",
            "pypdfium2",
            "cryptography",
            "lingua-language-detector",
            "Pillow",
            "ftfy",
            "bleach",
            "markdown2",
            "filelock",
            "orjson",
            "requests",
            "zstandard",
            "boto3",
            "httpx",
            "torch>=2.5.1",
            "transformers==4.46.2",
            "beaker-py",
        ]
        for package in required_packages:
            package_name = package.split('=')[0]
            try:
                importlib.import_module(package_name)
            except ImportError:
                subprocess.check_all(
                    [sys.executable, "-m", "pip", "install", package]
                )

    def _is_package_installed(self, package: str) -> bool:
        r"""Checks if a package is installed.

        Args:
            package (str): The package name to check.

        Returns:
            bool: True if installed, False otherwise.
        """
        try:
            importlib.import_module(package)
            return True
        except ImportError:
            return False

    def load(self, source: str, **kwargs: Any) -> str:
        r"""Processes the given PDF using olmOCR.

        Args:
            source (str): Path to the PDF file/files.

        Returns:
            str: Extracted text from the PDF.
        """
        if not os.path.exists(source):
            raise FileNotFoundError(f"File not found: {source}")
        workspace = self.config.get("workspace", "./workspace")
        command = [
            sys.executable,
            "-m",
            "olmocr.pipeline",
            workspace,
            "--pdfs",
            source,
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"olmOCR processing failed: {result.stderr}")
        return result.stdout

    @property
    def supported_formats(self) -> Set[str]:
        r"""Defines the supported file formats.

        Returns:
            Set[str]: Supported formats for OCR processing.
        """
        return {"pdf"}
