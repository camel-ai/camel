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
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class PptxNodeToolkit(BaseToolkit):
    r"""A toolkit for creating PowerPoint presentations using PptxGenJS
    (Node.js).
    """

    def __init__(
        self,
        working_directory: Optional[str] = None,
        timeout: Optional[float] = None,
        node_executable: str = "node",
    ) -> None:
        r"""Initialize the PptxNodeToolkit.

        Note:
            This toolkit requires Node.js to be installed and available in the
            system path (or specified via `node_executable`). It also requires
            the `pptxgenjs` npm package to be installed in the `scripts` dir.
        Args:
            working_directory (str, optional): The default directory for
                output files.
            timeout (Optional[float]): The timeout for the toolkit.
                (default: :obj:`None`)
            node_executable (str): The path to the Node.js executable.
                (default: "node")
        """
        super().__init__(timeout=timeout)
        self.node_executable = node_executable

        if working_directory:
            self.working_directory = Path(working_directory).resolve()
        else:
            camel_workdir = os.environ.get("CAMEL_WORKDIR")
            if camel_workdir:
                self.working_directory = Path(camel_workdir).resolve()
            else:
                self.working_directory = Path("./camel_working_dir").resolve()

        self.working_directory.mkdir(parents=True, exist_ok=True)
        self._check_node_environment()

    def _check_node_environment(self) -> None:
        """Checks if Node.js and the required scripts are available."""
        # 1. Check if node is available
        if not shutil.which(self.node_executable):
            logger.warning(
                f"Node.js executable '{self.node_executable}' not found. "
                "PptxNodeToolkit will not function correctly."
            )

        # 2. Check if the script's package.json dependencies are installed
        script_dir = Path(__file__).parent / "scripts"
        node_modules_path = script_dir / "node_modules"

        if not node_modules_path.exists():
            logger.warning(
                f"Node dependencies not found in {script_dir}. "
                "Please run `npm install` in that directory."
            )

    def _resolve_filepath(self, file_path: str) -> Path:
        path_obj = Path(file_path)
        if not path_obj.is_absolute():
            path_obj = self.working_directory / path_obj
        return path_obj.resolve()

    def create_presentation(
        self,
        content: Union[str, List[Dict[str, Any]]],
        filename: str,
    ) -> str:
        r"""Create a PowerPoint presentation (PPTX) file using PptxGenJS.

        The filename MUST end with ".pptx". If it does not, the toolkit will
        automatically append it.

        Args:
            content (Union[str, List[Dict[str, Any]]]): The content to write
                to the PPTX file. It can be a JSON string or a list of
                dictionaries/slides.

                Supported keys for each slide dictionary:
                - `title` (str): Title text for the slide.
                - `subtitle` (str): Subtitle text.
                - `heading` (str): Main heading for the slide.
                - `text` (str): Body text.
                - `bullet_points` (List[str]): A list of bullet point strings.
                - `table` (Dict): A dictionary with `headers` (List[str]) and
                  `rows` (List[List[str]]).

                Example Structure:
                [
                    {
                        "title": "Main Title",
                        "subtitle": "Subtitle text"
                    },
                    {
                        "heading": "Slide Heading",
                        "bullet_points": [
                            "Point 1",
                            "Point 2"
                        ]
                    },
                    {
                        "heading": "Table Slide",
                        "table": {
                            "headers": ["Col 1", "Col 2"],
                            "rows": [["A", "B"], ["C", "D"]]
                        }
                    }
                ]
            filename (str): The name of the file to save. MUST end in .pptx.

        Returns:
            str: A JSON string containing the result status, file path, and
                number of slides generated.
        """
        if not filename.lower().endswith('.pptx'):
            filename += '.pptx'

        # Ensure content is a valid JSON string or structure
        try:
            if not isinstance(content, str):
                # If it's a list/dict, check for expected keys if possible
                if isinstance(content, list):
                    for item in content:
                        if not isinstance(item, dict):
                            return "Error: Slide content must be a dictionary."
                        # Basic validation for known keys
                        valid_keys = {
                            "title",
                            "subtitle",
                            "heading",
                            "text",
                            "bullet_points",
                            "table",
                        }
                        if not any(key in item for key in valid_keys):
                            # Soft validation: warn/ignore if keys missing
                            pass
                content_str = json.dumps(content)
            else:
                # Validate JSON
                json_obj = json.loads(content)
                content_str = json.dumps(json_obj)
        except json.JSONDecodeError:
            return (
                "Error: Content must be valid JSON string or structure "
                "representing slides."
            )

        file_path = self._resolve_filepath(filename)
        script_path = Path(__file__).parent / "scripts" / "generate_pptx.js"

        try:
            # Run node script
            result = subprocess.run(
                [
                    self.node_executable,
                    str(script_path),
                    str(file_path),
                    content_str,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            return self._parse_script_output(result.stdout)

        except FileNotFoundError:
            return (
                f"Error: Node.js executable '{self.node_executable}' "
                "not found."
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating presentation: {e.stderr}")
            return f"Error creating presentation subprocess: {e.stderr}"
        except Exception as e:
            logger.error(f"Error creating presentation: {e!s}")
            return f"Error creating presentation: {e!s}"

    def create_presentation_from_js(
        self,
        js_code: str,
        filename: str,
    ) -> str:
        r"""Create a PowerPoint presentation by executing raw PptxGenJS code.

        This method allows for flexibility by letting the agent generate
        the exact JavaScript code needed to create the presentation using the
        PptxGenJS library.

        Args:
            js_code (str): The JavaScript code to execute. This code should
                use the `pptxgen` library (available globally or via require)
                and save the file to `filename`.
            filename (str): The name of the file to save.

        Returns:
            str: Status message.
        """
        if not filename.lower().endswith('.pptx'):
            filename += '.pptx'

        file_path = self._resolve_filepath(filename)
        script_dir = Path(__file__).parent / "scripts"

        # Create a temporary JS file in the scripts directory to ensure
        # it can find node_modules
        import uuid

        temp_js_filename = f"temp_gen_{uuid.uuid4()}.js"
        temp_js_path = script_dir / temp_js_filename

        try:
            with open(temp_js_path, "w", encoding="utf-8") as f:
                f.write(js_code)

            # Run node script
            result = subprocess.run(
                [self.node_executable, str(temp_js_path)],
                capture_output=True,
                text=True,
                check=True,
            )

            # Check if file exists first
            if file_path.exists():
                return f"Presentation created successfully at {file_path}"
            else:
                # Try to parse stdout if they followed our convention
                try:
                    return self._parse_script_output(result.stdout)
                except Exception:
                    return (
                        "Script executed but presentation file validation "
                        "failed or file not found."
                    )

        except FileNotFoundError:
            return (
                f"Error: Node.js executable '{self.node_executable}' "
                "not found."
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Error executing JS script: {e.stderr}")
            return f"Error executing JS script: {e.stderr}"
        except Exception as e:
            logger.error(f"Error executing JS script: {e!s}")
            return f"Error executing JS script: {e!s}"
        finally:
            # Cleanup temp file
            if temp_js_path.exists():
                os.remove(temp_js_path)

    def _parse_script_output(self, stdout: str) -> str:
        try:
            script_output = json.loads(stdout.strip())
            if script_output.get("success"):
                return (
                    f"Presentation created successfully. "
                    f"Path: {script_output.get('path')}, "
                    f"Slides: {script_output.get('slides')}"
                )
            else:
                return (
                    f"Error creating presentation: "
                    f"{script_output.get('error')}"
                )
        except json.JSONDecodeError:
            return f"Error parsing script output: {stdout.strip()}"

    def get_tools(self) -> list[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.create_presentation),
            FunctionTool(self.create_presentation_from_js),
        ]
