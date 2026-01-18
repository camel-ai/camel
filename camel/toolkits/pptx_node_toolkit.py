
import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class PptxNodeToolkit(BaseToolkit):
    r"""A toolkit for creating PowerPoint presentations using PptxGenJS (Node.js).
    """

    def __init__(
        self,
        working_directory: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initialize the PptxNodeToolkit.

        Args:
            working_directory (str, optional): The default directory for
                output files.
            timeout (Optional[float]): The timeout for the toolkit.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        if working_directory:
            self.working_directory = Path(working_directory).resolve()
        else:
            camel_workdir = os.environ.get("CAMEL_WORKDIR")
            if camel_workdir:
                self.working_directory = Path(camel_workdir).resolve()
            else:
                self.working_directory = Path("./camel_working_dir").resolve()

        self.working_directory.mkdir(parents=True, exist_ok=True)

    def _resolve_filepath(self, file_path: str) -> Path:
        path_obj = Path(file_path)
        if not path_obj.is_absolute():
            path_obj = self.working_directory / path_obj
        return path_obj.resolve()

    def create_presentation(
        self,
        content: str,
        filename: str,
    ) -> str:
        r"""Create a PowerPoint presentation (PPTX) file using PptxGenJS.
        
        The filename MUST end with ".pptx". If it does not, the toolkit will
        automatically append it, but the agent should strive to provide the
        correct extension.

        Args:
            content (str): The content to write to the PPTX file as a JSON
                string. It must be a list of dictionaries representing slides.
                
                JSON Schema Example:
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

        file_path = self._resolve_filepath(filename)
        script_path = Path(__file__).parent / "scripts" / "generate_pptx.js"

        try:
             # Ensure content is a valid JSON string
             try:
                 if not isinstance(content, str):
                     content_str = json.dumps(content)
                 else:
                     # Validate JSON
                     json_obj = json.loads(content)
                     content_str = json.dumps(json_obj)
             except json.JSONDecodeError:
                 return "Error: Content must be valid JSON string representing slides."

             # Run node script
             result = subprocess.run(
                 ["node", str(script_path), str(file_path), content_str],
                 capture_output=True,
                 text=True,
                 check=True
             )
             
             # Parse JSON output from script
             try:
                 script_output = json.loads(result.stdout.strip())
                 if script_output.get("success"):
                     return f"Presentation created successfully. Path: {script_output.get('path')}, Slides: {script_output.get('slides')}"
                 else:
                     return f"Error creating presentation: {script_output.get('error')}"
             except json.JSONDecodeError:
                 return f"Error parsing script output: {result.stdout.strip()}"

        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating presentation: {e.stderr}")
            return f"Error creating presentation subprocess: {e.stderr}"
        except Exception as e:
            logger.error(f"Error creating presentation: {str(e)}")
            return f"Error creating presentation: {str(e)}"

    def get_tools(self) -> list[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [FunctionTool(self.create_presentation)]
