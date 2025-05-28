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


import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class PPTXToolkit(BaseToolkit):
    r"""A toolkit for creating and writing PowerPoint presentations (PPTX files).

    This class provides cross-platform support for creating PPTX files with
    title slides, content slides, text formatting, and image embedding.
    """

    def __init__(
        self,
        output_dir: str = "./",
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initialize the PPTXToolkit.

        Args:
            output_dir (str): The default directory for output files.
                Defaults to the current working directory.
            timeout (Optional[float]): The timeout for the toolkit.
                (default: :obj: `None`)
        """
        super().__init__(timeout=timeout)
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"PPTXToolkit initialized with output directory: {self.output_dir}"
        )

    def _resolve_filepath(self, file_path: str) -> Path:
        r"""Convert the given string path to a Path object.

        If the provided path is not absolute, it is made relative to the
        default output directory. The filename part is sanitized to replace
        spaces and special characters with underscores, ensuring safe usage
        in downstream processing.

        Args:
            file_path (str): The file path to resolve.

        Returns:
            Path: A fully resolved (absolute) and sanitized Path object.
        """
        path_obj = Path(file_path)
        if not path_obj.is_absolute():
            path_obj = self.output_dir / path_obj

        sanitized_filename = self._sanitize_filename(path_obj.name)
        path_obj = path_obj.parent / sanitized_filename
        return path_obj.resolve()

    def _sanitize_filename(self, filename: str) -> str:
        r"""Sanitize a filename by replacing special characters and spaces.

        Args:
            filename (str): The filename to sanitize.

        Returns:
            str: The sanitized filename.
        """
        import re
        # Replace spaces and special characters with underscores
        sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        return sanitized

    def _write_pptx_file(
        self, file_path: Path, content: Union[str, list]
    ) -> None:
        r"""Write text content to a PPTX file with enhanced formatting.

        Args:
            file_path (Path): The target file path.
            content (Union[str, list]): The content to write to the PPTX file.
                Must be a list of dictionaries where:
                - First element: Title slide with keys 'title' and 'subtitle'
                - Subsequent elements: Content slides with keys 'title', 'text' (optional), 'image' (optional)
                
                Example format:
                [
                    {
                        "title": "Presentation Title",
                        "subtitle": "Presentation Subtitle"
                    },
                    {
                        "title": "Slide 1 Title",
                        "text": "Slide content text",
                        "image": "https://example.com/image.jpg"  # optional
                    },
                    {
                        "title": "Slide 2 Title", 
                        "text": "More content text"
                        # image field is optional
                    }
                ]

        Raises:
            ValueError: If content is not a list.
        """
        import pptx
        import requests
        from pptx.dml.color import RGBColor
        from pptx.util import Inches, Pt

        def format_text_runs(text_frame, font_name: str, font_size: int, bold: bool, color):
            """Apply formatting to all text runs in a text frame."""
            for paragraph in text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.name = font_name
                    run.font.size = Pt(font_size)
                    run.font.bold = bold
                    run.font.color.rgb = color

        def add_image_to_slide(slide, image_url: str):
            """Download and add an image to a slide with error handling."""
            try:
                response = requests.get(image_url, timeout=10)
                response.raise_for_status()
                image_stream = io.BytesIO(response.content)

                # Position image on the right side
                left = slide_width - image_width - margin_left
                top = margin_top + Inches(1.5)

                slide.shapes.add_picture(
                    image_stream, left, top, width=image_width, height=image_height
                )
            except Exception as e:
                logger.warning(f"Failed to load image from {image_url}: {e}")

        # Input validation
        if not isinstance(content, list):
            raise ValueError(
                f"PPTX content must be a list of dictionaries, got {type(content).__name__}"
            )

        presentation = pptx.Presentation()

        # Define standard dimensions and margins
        slide_width = Inches(10)
        margin_left = Inches(0.5)
        margin_top = Inches(1)
        image_width = Inches(4)
        image_height = Inches(3)

        # Process slides
        if content:
            # Title slide (first element)
            title_slide_data = content.pop(0) if content else {}
            title_layout = presentation.slide_layouts[0]
            title_slide = presentation.slides.add_slide(title_layout)

            # Set title and subtitle
            if title_slide.shapes.title:
                title_slide.shapes.title.text = title_slide_data.get("title", "")
                format_text_runs(
                    title_slide.shapes.title.text_frame, 
                    'Arial', 44, True, RGBColor(0, 0, 0)
                )

            if len(title_slide.placeholders) > 1:
                subtitle = title_slide.placeholders[1]
                subtitle.text = title_slide_data.get("subtitle", "")
                format_text_runs(
                    subtitle.text_frame, 'Arial', 24, False, RGBColor(64, 64, 64)
                )

            # Content slides
            for slide_data in content:
                if not isinstance(slide_data, dict):
                    continue
                    
                content_layout = presentation.slide_layouts[1]
                content_slide = presentation.slides.add_slide(content_layout)

                # Set slide title
                if content_slide.shapes.title:
                    content_slide.shapes.title.text = slide_data.get("title", "")
                    format_text_runs(
                        content_slide.shapes.title.text_frame,
                        'Arial', 36, True, RGBColor(0, 0, 0)
                    )

                # Set slide text
                slide_text = slide_data.get("text", "")
                if slide_text and len(content_slide.placeholders) > 1:
                    text_placeholder = content_slide.placeholders[1]
                    text_placeholder.text = slide_text
                    format_text_runs(
                        text_placeholder.text_frame,
                        'Arial', 18, False, RGBColor(64, 64, 64)
                    )

                # Add image if present
                image_url = slide_data.get("image")
                if image_url:
                    add_image_to_slide(content_slide, image_url)

        # Save the presentation
        presentation.save(str(file_path))
        logger.debug(f"Wrote PPTX to {file_path} with enhanced formatting")

    def create_presentation(
        self,
        content: str,
        filename: str,
    ) -> str:
        r"""Create a PowerPoint presentation (PPTX) file.

        Args:
            content (str): The content to write to the PPTX file as a JSON string.
                Must represent a list of dictionaries with specific structure:
                - First dict: title slide {"title": str, "subtitle": str}
                - Other dicts: content slides {"title": str, "text": str (optional), "image": str URL (optional)}
                
                Example JSON string:
                '[
                    {
                        "title": "Presentation Title",
                        "subtitle": "Presentation Subtitle"
                    },
                    {
                        "title": "Slide 1 Title",
                        "text": "Slide content text",
                        "image": "https://example.com/image.jpg"
                    }
                ]'
            filename (str): The name or path of the file. If a relative path is
                supplied, it is resolved to self.output_dir.

        Returns:
            str: A success message indicating the file was created.

        Raises:
            ValueError: If content is not valid JSON or file extension is not .pptx.
            FileNotFoundError: If the output directory does not exist.
            PermissionError: If there are insufficient permissions to write the file.
        """
        # Ensure filename has .pptx extension
        if not filename.lower().endswith('.pptx'):
            filename += '.pptx'

        # Resolve file path
        file_path = self._resolve_filepath(filename)

        # Parse and validate content format
        try:
            import json
            parsed_content = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Content must be valid JSON: {e}")

        if not isinstance(parsed_content, list):
            raise ValueError(
                f"PPTX content must be a list of dictionaries, got {type(parsed_content).__name__}"
            )

        try:
            # Create the PPTX file
            self._write_pptx_file(file_path, parsed_content.copy())
            
            success_msg = f"PowerPoint presentation successfully created: {file_path}"
            logger.info(success_msg)
            return success_msg

        except Exception as e:
            error_msg = f"Failed to create PPTX file {file_path}: {str(e)}"
            logger.error(error_msg)
            raise e

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [FunctionTool(self.create_presentation)] 