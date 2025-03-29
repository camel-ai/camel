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

import json
import mimetypes
import os
from typing import List, Literal, Optional, Tuple
from urllib.parse import urlparse

import chardet
import nest_asyncio
import pandas as pd
import requests
import xmltodict
from chunkr_ai import Chunkr
from docx2markdown._docx_to_markdown import docx_to_markdown
from openpyxl import load_workbook
from xls2xlsx import XLS2XLSX

from camel.logger import get_logger
from camel.models import BaseModelBackend
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.toolkits.image_analysis_toolkit import ImageAnalysisToolkit
from camel.utils import retry_on_error

nest_asyncio.apply()

logger = get_logger(__name__)


class DocumentProcessingToolkit(BaseToolkit):
    r"""A class representing a toolkit for processing document and return the
    content of the document.

    This class provides method for processing docx, pdf, pptx, excel, csv etc.
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        model: Optional[BaseModelBackend] = None,
    ):
        self.image_tool = ImageAnalysisToolkit(model=model)
        self.cache_dir = os.path.abspath(cache_dir or "tmp/")
        os.makedirs(self.cache_dir, exist_ok=True)

    def _convert_to_markdown(self, df: pd.DataFrame) -> str:
        r"""Convert DataFrame to Markdown format table.

        Args:
            df (pd.DataFrame): DataFrame containing the Excel data.

        Returns:
            str: Markdown formatted table.
        """
        from tabulate import tabulate

        md_table = tabulate(df, headers='keys', tablefmt='pipe')
        return str(md_table)

    def _detect_file_encoding(
        self, document_path: str, default_encoding: str = "utf-8"
    ) -> str:
        r"""Detects the encoding of a file using chardet.

        Args:
            document_path (str): The path of the file.

        Returns:
            str: The detected encoding type.
        """
        try:
            with open(document_path, "rb") as f:
                detected_encoding = chardet.detect(f.read())["encoding"]
                return detected_encoding or default_encoding
        except Exception as e:
            logger.warning(
                f"Encoding detection failed for {document_path}, "
                f"falling back to {default_encoding}. Error: {e}"
            )
            return default_encoding

    def extract_excel_content(
        self,
        document_path: str,
        header_only: bool,
        max_rows: Optional[int] = 100,
    ) -> str:
        r"""Extract detailed cell information from an Excel file, including
        multiple sheets.
        Args:
            document_path (str): The path of the Excel file.
            header_only (bool): Whether to return only headers or full content.
            max_rows (int, Optional): The maximum number of rows to process.
            (default: 100)
        Returns:
            str: Extracted excel information, including details of each sheet.
        """

        logger.debug(
            f"Calling extract_excel_content with document_path:{document_path}"
        )

        if not document_path.endswith(("xls", "xlsx", "csv")):
            logger.error("Only xls, xlsx, csv files are supported.")
            return f"Failed to process file {document_path}"

        try:
            if document_path.endswith("csv"):
                return self._process_csv(document_path, header_only, max_rows)

            return self._process_xlsx(document_path, header_only, max_rows)
        except Exception as e:
            logger.error(f"Error occurred while processing Excel file: {e}")
            return f"Failed to process file {document_path}: {e}"

    def _process_csv(
        self, document_path: str, header_only: bool, max_rows: Optional[int]
    ) -> str:
        r"""Handles processing csv files.
        Args:
            document_path (str): The path of the Excel file.
            header_only (bool): Whether to return only headers or full content.
            max_rows (int, Optional): The maximum number of rows to process.
        Returns:
            str: Extracted excel information, including details of each sheet.
        """
        encoding = self._detect_file_encoding(document_path)
        df = pd.read_csv(
            document_path,
            encoding=encoding,
            nrows=1 if header_only else max_rows,
        )
        df = df.dropna(how="all", axis=0).dropna(how="all", axis=1)

        headers = df.columns.tolist()
        if header_only:
            return f"CSV File Processed:\nHeaders: {headers}"

        md_table = self._convert_to_markdown(df)
        return f"CSV File Processed:\n{md_table}"

    def _process_xlsx(
        self, document_path: str, header_only: bool, max_rows: Optional[int]
    ) -> str:
        r"""Handles processing XLSX files.
        Args:
            document_path (str): The path of the Excel file.
            header_only (bool): Whether to return only headers or full content.
            max_rows (int, Optional): The maximum number of rows to process.
        Returns:
            str: Extracted excel information, including details of each sheet.
        """
        if document_path.endswith("xls"):
            output_path = document_path.replace(".xls", ".xlsx")
            XLS2XLSX(document_path).to_xlsx(output_path)
            document_path = output_path

        wb = load_workbook(document_path, data_only=True)
        sheet_info_list = []

        for sheet in wb.sheetnames:
            ws = wb[sheet]
            cell_info_list = [
                {
                    "index": f"{cell.row}{cell.column_letter}",
                    "value": cell.value,
                    "font_color": cell.font.color.rgb
                    if cell.font
                    and cell.font.color
                    and "rgb=None" not in str(cell.font.color)
                    else None,
                    "fill_color": cell.fill.fgColor.rgb
                    if cell.fill
                    and cell.fill.fgColor
                    and "rgb=None" not in str(cell.fill.fgColor)
                    else None,
                }
                for row in ws.iter_rows()
                for cell in row
            ]

            sheet_df = pd.read_excel(
                document_path, sheet_name=sheet, engine='openpyxl'
            )
            sheet_df.dropna(how='all', inplace=True)
            sheet_df.dropna(axis=1, how='all', inplace=True)
            if header_only:
                sheet_df = sheet_df.head(0)
            if max_rows:
                sheet_df = sheet_df.head(max_rows)

            markdown_content = self._convert_to_markdown(sheet_df)
            sheet_info_list.append(
                {
                    "sheet_name": sheet,
                    "cell_info_list": cell_info_list,
                    "markdown_content": markdown_content,
                }
            )

        result_str = ""
        for sheet_info in sheet_info_list:
            result_str += f"""
            Sheet Name: {sheet_info['sheet_name']}
            Cell information list:
            {sheet_info['cell_info_list']}
            
            Markdown View of the content:
            {sheet_info['markdown_content']}
            
            {'-'*40}
            """
        return result_str

    @retry_on_error()
    def extract_document_content(self, document_path: str) -> Tuple[bool, str]:
        r"""Extract the content of a given document (or url) and return text.
        It may filter out some information, resulting in inaccurate content.

        Args:
            document_path (str): The path of the document to be processed,
            either a local path or a URL. It can process image,
            audio files, zip files and webpages, etc.

        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating whether
            the document was processed successfully, and the content of the
            document (if success).
        """
        import asyncio

        logger.debug(
            f"Calling extract_document_content function with document_path=\
            `{document_path}`"
        )

        if any(
            document_path.endswith(ext) for ext in [".jpg", ".jpeg", ".png"]
        ):
            res = self.image_tool.ask_question_about_image(
                document_path,
                "Please make a detailed caption about the image.",
            )
            return True, res

        if any(document_path.endswith(ext) for ext in ["xls", "xlsx", "csv"]):
            res = self.extract_excel_content(document_path, False)
            return True, res

        if any(document_path.endswith(ext) for ext in ["zip"]):
            extracted_files = self._unzip_file(document_path)
            return True, f"The extracted files are: {extracted_files}"

        if any(
            document_path.endswith(ext) for ext in ["json", "jsonl", "jsonld"]
        ):
            encoding = self._detect_file_encoding(document_path)
            with open(document_path, "r", encoding=encoding) as f:
                content = json.load(f)
            return True, content

        if any(document_path.endswith(ext) for ext in ["py"]):
            encoding = self._detect_file_encoding(document_path)
            with open(document_path, "r", encoding=encoding) as f:
                content = f.read()
            return True, content

        if any(document_path.endswith(ext) for ext in ["xml"]):
            data = None
            encoding = self._detect_file_encoding(document_path)
            with open(document_path, "r", encoding=encoding) as f:
                content = f.read()

            try:
                data = xmltodict.parse(content)
                logger.debug(f"The extracted xml data is: {data}")
                return True, json.dumps(data)

            except Exception:
                logger.debug(f"The raw xml data is: {content}")
                return True, content

        if self._is_webpage(document_path):
            extracted_text = self._extract_webpage_content(document_path)
            return True, extracted_text

        else:
            # judge if url
            parsed_url = urlparse(document_path)
            is_url = all([parsed_url.scheme, parsed_url.netloc])
            if not is_url:
                if not os.path.exists(document_path):
                    return (
                        False,
                        f"Document not found at path: {document_path}.",
                    )

            # if is docx file, use docx2markdown to convert it
            if document_path.endswith(".docx"):
                if is_url:
                    tmp_path = self._download_file(document_path)
                else:
                    tmp_path = document_path

                file_name = os.path.basename(tmp_path)
                md_file_path = f"{file_name}.md"
                docx_to_markdown(tmp_path, md_file_path)

                # load content of md file
                with open(md_file_path, "r") as f:
                    extracted_text = f.read()
                return True, extracted_text
            try:
                result = asyncio.run(
                    self._extract_content_with_chunkr(document_path)
                )
                return True, result

            except Exception as e:
                logger.warning(
                    f"Error occurred while using Chunkr to process document:\
                    {e}"
                )
                if document_path.endswith(".pdf"):
                    # try using pypdf to extract text from pdf
                    try:
                        from PyPDF2 import PdfReader

                        if is_url:
                            tmp_path = self._download_file(document_path)
                            document_path = tmp_path

                        # Open file in binary mode for PdfReader
                        with open(document_path, "rb") as f:
                            reader = PdfReader(f)
                            extracted_text = ""
                            for page in reader.pages:
                                extracted_text += page.extract_text()

                        return True, extracted_text

                    except Exception as pdf_error:
                        logger.error(
                            f"Error occurred while processing pdf: {pdf_error}"
                        )
                        return (
                            False,
                            f"Error occurred while processing pdf:\
                            {pdf_error}",
                        )

                logger.error(f"Error occurred while processing document: {e}")
                return False, f"Error occurred while processing document: {e}"

    def _is_webpage(self, url: str) -> bool:
        r"""Judge whether the given URL is a webpage."""
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

    @retry_on_error()
    async def _extract_content_with_chunkr(
        self,
        document_path: str,
        output_format: Literal["json", "markdown"] = "markdown",
    ) -> str:
        chunkr = Chunkr(api_key=os.getenv("CHUNKR_API_KEY"))

        result = await chunkr.upload(document_path)

        if result.status == "Failed":
            logger.error(
                f"Error while processing document {document_path}:\
                {result.message} using Chunkr."
            )
            return f"Error while processing document: {result.message}"

        # extract document name
        document_name = os.path.basename(document_path)
        output_file_path: str

        if output_format == "json":
            output_file_path = f"{document_name}.json"
            result.json(output_file_path)

        elif output_format == "markdown":
            output_file_path = f"{document_name}.md"
            result.markdown(output_file_path)

        else:
            return "Invalid output format."

        with open(output_file_path, "r") as f:
            extracted_text = f.read()
        f.close()
        return extracted_text

    @retry_on_error()
    def _extract_webpage_content(self, url: str) -> str:
        api_key = os.getenv("FIRECRAWL_API_KEY")
        from firecrawl import FirecrawlApp

        # Initialize the FirecrawlApp with your API key
        app = FirecrawlApp(api_key=api_key)

        data = app.crawl_url(
            url,
            params={"limit": 1, "scrapeOptions": {"formats": ["markdown"]}},
        )
        logger.debug(f"Extracted data from {url}: {data}")
        if len(data["data"]) == 0:
            if data["success"]:
                return "No content found on the webpage."
            else:
                return "Error while crawling the webpage."

        return str(data["data"][0]["markdown"])

    def _download_file(self, url: str):
        r"""Download a file from a URL and save it to the cache directory."""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            file_name = url.split("/")[-1]

            file_path = os.path.join(self.cache_dir, file_name)

            with open(file_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            return file_path

        except requests.exceptions.RequestException as e:
            print(f"Error downloading the file: {e}")

    def _get_formatted_time(self) -> str:
        import time

        return time.strftime("%m%d%H%M")

    def _unzip_file(self, zip_path: str) -> List[str]:
        import zipfile

        if not zipfile.is_zipfile(zip_path):
            raise ValueError("File is not a valid ZIP archive")

        zip_name = os.path.splitext(os.path.basename(zip_path))[0]
        extract_path = os.path.join(self.cache_dir, zip_name)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        return [
            os.path.join(root, f)
            for root, _, files in os.walk(extract_path)
            for f in files
        ]

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
            representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.extract_document_content),
            FunctionTool(self.extract_excel_content),
        ]
