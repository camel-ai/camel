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

import asyncio
from typing import Optional, List
import os
import venv
import tempfile
import shutil
import subprocess

from camel.verifiers import BaseVerifier
from .models import Response, VerificationResult, VerificationStatus
from camel.logger import get_logger

logger = get_logger(__name__)

class PythonVerifier(BaseVerifier):
    def __init__(self, python_version: str = "python3", timeout: Optional[float] = 30.0, required_packages: Optional[List[str]] = None):
        super().__init__(timeout=timeout)
        self.python_version = python_version
        self.venv_path = None
        self.required_packages = required_packages or []

    async def _setup(self) -> None:
        r"""Set up a virtual environment for execution 
        and install required packages."""
        self.venv_path = tempfile.mkdtemp()
        venv.create(self.venv_path, with_pip=True)
        logger.info(f"Virtual environment created at {self.venv_path}")

        venv_pip = os.path.join(self.venv_path, "bin", "pip")

        if self.required_packages:
            try:
                subprocess.run([venv_pip, "install"] + self.required_packages, check=True, capture_output=True)
                logger.info(f"Installed required packages: {', '.join(self.required_packages)}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install required packages: {e.stderr.decode().strip()}")

    async def _teardown(self) -> None:
        r"""Clean up the virtual environment."""
        if self.venv_path:
            shutil.rmtree(self.venv_path)
            logger.info(f"Virtual environment at {self.venv_path} removed")
            self.venv_path = None

    async def _verify_implementation(self, result: Response) -> VerificationResult:
        r"""Executes the LLM-generated response in a Python virtual environment."""
        if not self.venv_path:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                error_message="Virtual environment is not set up.",
            )

        script = result.llm_response.strip()
        venv_python = os.path.join(self.venv_path, "bin", "python")

        if not os.path.exists(venv_python):
            return VerificationResult(
                status=VerificationStatus.ERROR,
                error_message="Python binary not found in virtual environment.",
            )

        try:
            process = await asyncio.create_subprocess_exec(
                venv_python, "-c", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self._timeout)

            if process.returncode == 0:
                return VerificationResult(
                    status=VerificationStatus.SUCCESS,
                    result=stdout.decode().strip(),
                )
            else:
                return VerificationResult(
                    status=VerificationStatus.ERROR,
                    error_message=stderr.decode().strip(),
                    result=stdout.decode().strip(),
                )

        except asyncio.TimeoutError:
            return VerificationResult(
                status=VerificationStatus.TIMEOUT,
                error_message="Execution timed out.",
            )

        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                error_message=f"Execution error: {e}",
            )
