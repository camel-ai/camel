
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

        Args:
            content (str): The content to write to the PPTX file as a JSON
                string.
            filename (str): The name or path of the file.

        Returns:
            str: A success message indicating the file was created.
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
             res = result.stdout.strip()
             return res

        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating presentation: {e.stderr}")
            return f"Error creating presentation: {e.stderr}"
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
