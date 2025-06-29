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

from __future__ import annotations

import asyncio
import hashlib
import traceback
import zipfile
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from urllib.parse import urlparse

import requests

from camel.logger import get_logger
from camel.models import BaseModelBackend
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.toolkits import ImageAnalysisToolkit
from camel.utils.commons import dependencies_required
from camel.utils import retry_on_error, MCPServer
from camel.loaders import MarkItDownLoader


logger = get_logger(__name__)


_TEXT_EXTS: Set[str] = {".txt", ".md", ".rtf"}
_DOC_EXTS: Set[str] = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".odt"}
_IMAGE_EXTS: Set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
_EXCEL_EXTS: Set[str] = {".xls", ".xlsx", ".csv"}
_ARCHIVE_EXTS: Set[str] = {".zip"}
_WEB_EXTS: Set[str] = {".html", ".htm", ".xml"}
_CODE_EXTS: Set[str] = {".py", ".js", ".java", ".cpp", ".c", ".go", ".rs"}
_DATA_EXTS: Set[str] = {".json", ".jsonl", ".jsonld", ".xml"}


class _LoaderWrapper:
    r"""Uniform interface wrapper for different document loaders.

    Every loader exposes convert_file(path) -> str method for consistent usage.
    """

    def __init__(self, loader: object):
        r"""Initialize the loader wrapper.

        Args:
            loader (object): The underlying loader instance.
        """
        self._loader = loader

    def convert_file(self, path: str) -> str:
        r"""Convert a file to plain text using the wrapped loader.

        Args:
            path (str): Path to the file to be converted.

        Returns:
            str: The extracted plain text content.

        Raises:
            AttributeError: If the loader doesn't support required methods.
            RuntimeError: If the loader fails to parse the file.
        """
        if hasattr(self._loader, "convert_file"):
            return self._loader.convert_file(path)  # type: ignore[attr-defined]
        raise AttributeError("Loader must expose convert_file method")


def _init_loader(loader_type: str, loader_kwargs: Optional[dict] | None) -> _LoaderWrapper:
    r"""Initialize a document loader based on the specified type.

    Args:
        loader_type (str): Type of loader to initialize ('markitdown').
        loader_kwargs (Optional[dict]): Additional keyword arguments for the loader.

    Returns:
        _LoaderWrapper: Wrapped loader instance.

    Raises:
        ImportError: If the required loader is not available.
        ValueError: If the loader type is not supported.
    """
    loader_type = loader_type.lower()
    loader_kwargs = loader_kwargs or {}

    if loader_type == "markitdown":
        if MarkItDownLoader is None:
            raise ImportError(
                "MarkItDownLoader unavailable – install `camel-ai[docs]` or `markitdown`."
            )
        return _LoaderWrapper(MarkItDownLoader(**loader_kwargs))

    raise ValueError("Unsupported loader_type. Only 'markitdown' is supported.")


@MCPServer()
class DocumentToolkit(BaseToolkit):
    r"""A comprehensive toolkit for processing various document formats.

    This toolkit can extract plain-text content from local files, remote URLs,
    ZIP archives, and webpages. It supports images, Office documents, PDFs,
    Excel files, code files, and more.
    """

    def __init__(
            self,
            *,
            cache_dir: str | Path | None = None,
            model: Optional[BaseModelBackend] = None,
            loader_type: str = "markitdown",
            loader_kwargs: Optional[dict] = None,
            enable_cache: bool = True,
    ) -> None:
        r"""Initialize the DocumentToolkit.

        Args:
            cache_dir (str | Path | None): Directory for caching processed documents.
                Defaults to ~/.cache/camel/documents.
            model (Optional[object]): Model backend for image analysis.
            loader_type (str): Primary document loader type ('markitdown').
            loader_kwargs (Optional[dict]): Additional arguments for the primary loader.
            enable_cache (bool): Whether to enable disk and memory caching.
        """
        super().__init__()

        # Initialize paths and cache settings
        self.cache_dir: Path = Path(cache_dir or "~/.cache/camel/documents").expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.enable_cache = enable_cache

        # Initialize specialized toolkits for specific file types
        self.image_tool = ImageAnalysisToolkit(model=model)

        # Initialize primary document loader
        self._loader = _init_loader(loader_type, loader_kwargs)
        logger.info("DocumentProcessingToolkit initialised with %s loader", loader_type)

        # Initialize optional MarkItDown loader for improved Office/PDF support
        if MarkItDownLoader is not None:
            try:
                self.mid_loader = MarkItDownLoader()
            except Exception as e:  # pragma: no cover
                logger.debug("Falling back – MarkItDown initialisation failed: %s", e)
                self.mid_loader = None
        else:
            self.mid_loader = None

        # Initialize in-memory cache (keyed by SHA-256 of path + mtime)
        self._cache: Dict[str, str] = {}


    # Public API methods
    @retry_on_error()
    def extract_document_content(self, document_path: str) -> Tuple[bool, str]:
        r"""Extract the content of a given document (or URL) and return the processed text.

        It may filter out some information, resulting in inaccurate content.

        Args:
            document_path (str): The path of the document to be processed, either a local path
                or a URL. It can process image, audio files, zip files and webpages, etc.

        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating whether the document
                was processed successfully, and the content of the document (if success).
        """
        try:
            cache_key = self._hash_key(document_path)
            if self.enable_cache and cache_key in self._cache:
                logger.debug("Cache hit: %s", document_path)
                return True, self._cache[cache_key]

            # Get file extension first
            suffix = f".{document_path.lower().rsplit('.', 1)[-1]}" if "." in document_path else ""
            is_url = self._is_url(document_path)  # Helper to check if it's a URL

            # For URLs with file extensions, download first then process
            if is_url and suffix and suffix not in _WEB_EXTS:
                local_path = self._download_file(document_path)
                document_path = str(local_path)

            # Process different file types with specialized handlers
            if suffix in _IMAGE_EXTS:
                ok, txt = self._handle_image(document_path)
                return self._cache_and_return(cache_key, ok, txt)

            if suffix in _EXCEL_EXTS:
                ok, txt = self._handle_excel(document_path)
                return self._cache_and_return(cache_key, ok, txt)

            if suffix in _ARCHIVE_EXTS:
                ok, txt = self._handle_zip(document_path)
                return self._cache_and_return(cache_key, ok, txt)

            if suffix in _DATA_EXTS:
                ok, txt = self._handle_data_file(document_path)
                return self._cache_and_return(cache_key, ok, txt)

            if suffix in _CODE_EXTS:
                ok, txt = self._handle_code_file(document_path)
                return self._cache_and_return(cache_key, ok, txt)

            if suffix in _TEXT_EXTS:
                ok, txt = self._handle_text_file(document_path)
                return self._cache_and_return(cache_key, ok, txt)

            if suffix in _WEB_EXTS:
                ok, txt = self._handle_html_file(document_path)
                return self._cache_and_return(cache_key, ok, txt)

            # Handle Office/PDF documents with preferred loader
            if suffix in _DOC_EXTS:
                if getattr(self, "mid_loader", None) is not None:
                    txt = self.mid_loader.convert_file(document_path)  # type: ignore[attr-defined]
                    return self._cache_and_return(cache_key, True, txt)
                else:
                    logger.warning("No suitable loader for DOC/PDF – falling back to generic loader")

            if self._is_webpage(document_path):
                ok, txt = self._handle_webpage(document_path)
                return self._cache_and_return(cache_key, ok, txt)

            # Fallback to generic loader
            txt = self._loader.convert_file(document_path)
            return self._cache_and_return(cache_key, True, txt)

        except Exception as exc:  # pragma: no cover
            logger.error("Failed to extract %s: %s", document_path, exc)
            logger.debug(traceback.format_exc())
            return False, f"Error extracting document {document_path}: {exc}"

    def _is_url(self, path: str) -> bool:
        """Check if the path is a URL."""
        parsed = urlparse(path)
        return bool(parsed.scheme and parsed.netloc)

    # Webpage processing methods (ported from original code)
    def _is_webpage(self, url: str) -> bool:
        r"""Determine whether the given URL points to a webpage.

        Args:
            url (str): The URL to check.

        Returns:
            bool: True if the URL is a webpage, False otherwise.
        """
        try:
            parsed_url = urlparse(url)
            is_url = all([parsed_url.scheme, parsed_url.netloc])
            if not is_url:
                return False

            path = parsed_url.path
            file_type, _ = mimetypes.guess_type(path)
            if file_type is not None and "text/html" in file_type:
                return True

            response = requests.head(url, allow_redirects=True, timeout=10)
            content_type = response.headers.get("Content-Type", "").lower()

            if "text/html" in content_type:
                return True
            else:
                return False

        except requests.exceptions.RequestException as e:
            logger.warning(f"Error while checking the URL: {e}")
            return False
        except TypeError:
            return True

    def _handle_webpage(self, url: str) -> Tuple[bool, str]:
        r"""Extract content from a webpage URL.

        Args:
            url (str): The URL of the webpage to process.

        Returns:
            Tuple[bool, str]: Success status and extracted content.
        """
        try:
            extracted_text = self._extract_webpage_content(url)
            return True, extracted_text
        except Exception as e:
            logger.warning(f"FireCrawl failed for {url}: {e}, falling back to MarkItDown")
            try:
                # Try using MarkItDown as fallback
                if self.mid_loader is not None:
                    txt = self.mid_loader.convert_file(url)  # type: ignore[attr-defined]
                    return True, txt
                else:
                    return False, "No suitable loader for webpage processing."
            except Exception as e2:
                logger.error(f"All webpage processing methods failed for {url}: {e2}")
                return False, f"Failed to extract content from the webpage: {e2}"

    @retry_on_error()
    @dependencies_required('crawl4ai')
    def _extract_webpage_content(self, url: str) -> str:
        r"""Extract webpage content using the Crawl4AI loader.

        Args:
            url (str): The URL of the webpage to extract content from.

        Returns:
            str: The extracted webpage content in markdown format.

        Raises:
            ImportError: If Crawl4AI library is not available.
            Exception: If scraping fails or returns no content.
        """
        from camel.loaders import Crawl4AI

        # Initialize Crawl4AI crawler
        crawler = Crawl4AI()

        try:
            # Use asyncio to run the async scrape method
            import asyncio
            scrape_result = asyncio.run(crawler.scrape(url))

            logger.debug(f"Extracted data from {url}: {scrape_result}")

            # Extract markdown content from the result
            if scrape_result and 'markdown' in scrape_result:
                markdown_content = scrape_result['markdown']
                if markdown_content:
                    return str(markdown_content)
                else:
                    return "No content found on the webpage."
            else:
                return "Error while crawling the webpage."

        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return f"Error while crawling the webpage: {str(e)}"


    # Specialized file type handlers
    def _handle_image(self, path: str) -> Tuple[bool, str]:
        r"""Process image files using the image analysis toolkit.

        Args:
            path (str): Path to the image file.

        Returns:
            Tuple[bool, str]: Success status and image description.
        """
        try:
            res = self.image_tool.ask_question_about_image(
                path, "Please make a detailed caption about the image."
            )
            return True, res
        except Exception as e:
            return False, f"Error processing image {path}: {e}"

    @dependencies_required('tabulate')
    def _convert_to_markdown(self, df: 'pd.DataFrame') -> str:
        r"""Convert DataFrame to Markdown format table."""
        from tabulate import tabulate

        md_table = tabulate(df, headers='keys', tablefmt='pipe')
        return str(md_table)

    @dependencies_required('pandas', 'openpyxl', 'xls2xlsx')
    def _extract_excel_content(self, document_path: str) -> str:
        r"""Extract detailed cell information from an Excel file, including
        multiple sheets.

        Args:
            document_path (str): The path of the Excel file.

        Returns:
            str: Extracted excel information, including details of each sheet.
        """
        import pandas as pd
        from openpyxl import load_workbook
        from xls2xlsx import XLS2XLSX

        logger.debug(
            f"Calling extract_excel_content with document_path: {document_path}"
        )

        if not (
                document_path.endswith("xls")
                or document_path.endswith("xlsx")
                or document_path.endswith("csv")
        ):
            logger.error("Only xls, xlsx, csv files are supported.")
            return (
                f"Failed to process file {document_path}: "
                f"It is not excel format. Please try other ways."
            )

        if document_path.endswith("csv"):
            try:
                df = pd.read_csv(document_path)
                md_table = self._convert_to_markdown(df)
                return f"CSV File Processed:\n{md_table}"
            except Exception as e:
                logger.error(f"Failed to process file {document_path}: {e}")
                return f"Failed to process file {document_path}: {e}"

        if document_path.endswith("xls"):
            output_path = document_path.replace(".xls", ".xlsx")
            x2x = XLS2XLSX(document_path)
            x2x.to_xlsx(output_path)
            document_path = output_path

        # Load the Excel workbook
        wb = load_workbook(document_path, data_only=True)
        sheet_info_list = []

        # Iterate through all sheets
        for sheet in wb.sheetnames:
            ws = wb[sheet]
            cell_info_list = []

            for row in ws.iter_rows():
                for cell in row:
                    row_num = cell.row
                    col_letter = cell.column_letter

                    cell_value = cell.value

                    font_color = None
                    if (
                            cell.font
                            and cell.font.color
                            and "rgb=None" not in str(cell.font.color)
                    ):  # Handle font color
                        font_color = cell.font.color.rgb

                    fill_color = None
                    if (
                            cell.fill
                            and cell.fill.fgColor
                            and "rgb=None" not in str(cell.fill.fgColor)
                    ):  # Handle fill color
                        fill_color = cell.fill.fgColor.rgb

                    cell_info_list.append(
                        {
                            "index": f"{row_num}{col_letter}",
                            "value": cell_value,
                            "font_color": font_color,
                            "fill_color": fill_color,
                        }
                    )

            # Convert the sheet to a DataFrame and then to markdown
            sheet_df = pd.read_excel(
                document_path, sheet_name=sheet, engine='openpyxl'
            )
            markdown_content = self._convert_to_markdown(sheet_df)

            # Collect all information for the sheet
            sheet_info = {
                "sheet_name": sheet,
                "cell_info_list": cell_info_list,
                "markdown_content": markdown_content,
            }
            sheet_info_list.append(sheet_info)

        result_str = ""
        for sheet_info in sheet_info_list:
            result_str += f"""
            Sheet Name: {sheet_info['sheet_name']}
            Cell information list:
            {sheet_info['cell_info_list']}

            Markdown View of the content:
            {sheet_info['markdown_content']}

            {'-' * 40}
            """

        return result_str

    def _handle_excel(self, path: str) -> Tuple[bool, str]:
        r"""Process Excel and CSV files using integrated Excel processing.

        Args:
            path (str): Path to the Excel or CSV file.

        Returns:
            Tuple[bool, str]: Success status and Excel content.
        """
        try:
            res = self._extract_excel_content(path)
            # Check if the result indicates an error
            if res.startswith("Failed to process file"):
                return False, res
            return True, res
        except Exception as e:
            logger.error(f"Error processing Excel file {path}: {e}")
            return False, f"Error processing Excel file {path}: {e}"

    def _handle_data_file(self, path: str) -> Tuple[bool, str]:
        r"""Process structured data files (JSON, XML).

        Args:
            path (str): Path to the data file.

        Returns:
            Tuple[bool, str]: Success status and parsed data content.
        """
        try:
            import json
            import xmltodict

            suffix = Path(path).suffix.lower()

            if suffix in [".json", ".jsonl", ".jsonld"]:
                with open(path, "r", encoding="utf-8") as f:
                    if suffix == ".jsonl":
                        # Handle JSON Lines format
                        lines = []
                        for line in f:
                            lines.append(json.loads(line.strip()))
                        content = lines
                    else:
                        content = json.load(f)
                return True, str(content)

            elif suffix == ".xml":
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                try:
                    data = xmltodict.parse(content)
                    logger.debug(f"The extracted xml data is: {data}")
                    return True, str(data)
                except Exception:
                    logger.debug(f"The raw xml data is: {content}")
                    return True, content

            return False, f"Unsupported data file format: {suffix}"
        except Exception as e:
            return False, f"Error processing data file {path}: {e}"

    def _handle_code_file(self, path: str) -> Tuple[bool, str]:
        r"""Process source code files by reading them as plain text.

        Args:
            path (str): Path to the code file.

        Returns:
            Tuple[bool, str]: Success status and code content.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return True, content
        except Exception as e:
            return False, f"Error processing code file {path}: {e}"

    def _handle_text_file(self, path: str) -> Tuple[bool, str]:
        r"""Process plain text files by reading them directly.

        Args:
            path (str): Path to the text file.

        Returns:
            Tuple[bool, str]: Success status and text content.
        """
        try:
            text = Path(path).expanduser().read_text(encoding="utf-8")
            return True, text
        except Exception as e:
            return False, f"Error reading text file {path}: {e}"

    def _handle_html_file(self, path: str) -> Tuple[bool, str]:
        r"""Process local HTML/XML files.

        Args:
            path (str): Path to the HTML/XML file.

        Returns:
            Tuple[bool, str]: Success status and processed content.
        """
        try:
            # Try using the generic loader first
            txt = self._loader.convert_file(path)
            return True, txt
        except Exception as e:
            # Fallback to raw text reading
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                return True, content
            except Exception as e2:
                return False, f"Error processing HTML file {path}: {e2}"

    # ZIP archive processing methods
    def _handle_zip(self, path_or_url: str) -> Tuple[bool, str]:
        r"""Process ZIP archive files by extracting and processing all contained files.

        Args:
            path_or_url (str): Path or URL to the ZIP file.

        Returns:
            Tuple[bool, str]: Success status and combined content of all files.
        """
        try:
            zip_path = self._ensure_local_zip(path_or_url)
            extract_dir = self.cache_dir / f"unzip_{self._short_hash(zip_path)}"
            extract_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
                # Log the files in the ZIP
                logger.info(f"ZIP contains files: {zf.namelist()}")

            parts: List[str] = []
            failed_files: List[str] = []

            for file in extract_dir.rglob("*"):
                if file.is_file():
                    logger.info(f"Processing file: {file}")
                    ok, text = self.extract_document_content(str(file))
                    if ok:
                        parts.append(f"=== File: {file.name} ===\n{text}")
                    else:
                        failed_files.append(f"{file.name}: {text}")

            if failed_files:
                logger.warning(f"Failed to process files: {failed_files}")

            result = "\n\n".join(parts) if parts else ""
            if failed_files:
                result += f"\n\nFailed to process:\n" + "\n".join(failed_files)

            return True, result
        except Exception as exc:
            logger.error("ZIP processing failed for %s: %s", path_or_url, exc)
            logger.debug(traceback.format_exc())
            return False, f"Error processing ZIP {path_or_url}: {exc}"

    def _ensure_local_zip(self, path_or_url: str) -> Path:
        r"""Ensure ZIP file is available locally, downloading if necessary.

        Args:
            path_or_url (str): Path or URL to the ZIP file.

        Returns:
            Path: Local path to the ZIP file.
        """
        parsed = urlparse(path_or_url)
        if parsed.scheme in {"http", "https"}:
            return self._download_file(path_or_url)
        return Path(path_or_url).expanduser().resolve()

    def _download_file(self, url: str) -> Path:
        r"""Download a file from URL to the local cache directory."""
        import re

        try:
            resp = requests.get(url, stream=True, timeout=60)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to download %s: %s", url, e)
            raise

        # Try to get filename from Content-Disposition header
        cd = resp.headers.get("Content-Disposition", "")
        filename = None
        if "filename" in cd:
            match = re.findall(r'filename[*]?=["\']?([^"\';\r\n]+)', cd)
            if match:
                filename = match[0].strip()

        # Fallback: get filename from URL
        if not filename:
            parsed_url = urlparse(url)
            filename = Path(parsed_url.path).name or "downloaded_file"

            # If no extension, guess from content type
            if not Path(filename).suffix:
                content_type = resp.headers.get("Content-Type", "").split(';')[0].strip()
                ext_map = {
                    "application/pdf": ".pdf",
                    "application/zip": ".zip",
                    "application/json": ".json",
                    "text/html": ".html",
                    "application/msword": ".doc",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
                    "application/vnd.ms-excel": ".xls",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                    "image/jpeg": ".jpg",
                    "image/png": ".png",
                    "image/gif": ".gif",
                    "image/webp": ".webp",
                    "text/plain": ".txt",
                    "text/csv": ".csv"
                }
                ext = ext_map.get(content_type, "")
                filename += ext

        # Sanitize filename for filesystem
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

        local_path = self.cache_dir / filename
        logger.info("Downloading %s → %s", url, local_path)

        try:
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
        except IOError as e:
            logger.error("Failed to save file %s: %s", local_path, e)
            raise

        return local_path

    # Cache management methods
    def _cache_and_return(self, key: str, ok: bool, value: str) -> Tuple[bool, str]:
        r"""Store successful results in cache and return the result tuple.

        Args:
            key (str): Cache key for storing the result.
            ok (bool): Success status of the operation.
            value (str): The processed content.

        Returns:
            Tuple[bool, str]: The input success status and value.
        """
        if ok and self.enable_cache:
            self._cache[key] = value
            try:
                (self.cache_dir / f"{key}.txt").write_text(value, encoding="utf-8")
            except Exception as e:  # pragma: no cover
                logger.debug("Cache write failed: %s", e)
        return ok, value

    # Hash generation utilities
    def _hash_key(self, path: str) -> str:
        r"""Generate a stable cache key using SHA-256 hash of path and modification time.

        Args:
            path (str): File path or URL to generate key for.

        Returns:
            str: SHA-256 hash string to use as cache key.
        """
        if self._is_webpage(path):
            # For URLs, use the URL itself as the key component
            return hashlib.sha256(f"{path}:url".encode()).hexdigest()

        p = Path(path)
        mtime = p.stat().st_mtime if p.exists() else 0
        return hashlib.sha256(f"{path}:{mtime}".encode()).hexdigest()

    def _short_hash(self, path: Path) -> str:
        r"""Generate a short hash for directory naming.

        Args:
            path (Path): Path to generate hash for.

        Returns:
            str: Short (8-character) hash string.
        """
        return hashlib.sha256(str(path).encode()).hexdigest()[:8]


    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [FunctionTool(self.extract_document_content)]


    async def _extract_async(self, document_path: str) -> str:
        r"""Asynchronous wrapper for document extraction (rarely used).

        Args:
            document_path (str): Path to the document to extract.

        Returns:
            str: Extracted document content.
        """
        return self._loader.convert_file(document_path)

    def extract_document_content_sync(self, document_path: str) -> Tuple[bool, str]:
        r"""Synchronous wrapper for environments without asyncio support.

        Args:
            document_path (str): Path to the document to extract.

        Returns:
            Tuple[bool, str]: Success status and extracted content.
        """
        loop = (
            asyncio.get_event_loop()
            if asyncio.get_event_loop().is_running()
            else asyncio.new_event_loop()
        )
        return loop.run_until_complete(self.extract_document_content(document_path))