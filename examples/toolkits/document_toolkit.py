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

import logging
import tempfile
import time
import zipfile
from pathlib import Path
from typing import ClassVar, Optional

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    RequestException,
    Timeout,
)
from urllib3.util.retry import Retry

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import DocumentToolkit
from camel.types import ModelPlatformType, ModelType

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NetworkConfig:
    """Configuration for network requests."""

    TIMEOUT: ClassVar[tuple[int, int]] = (
        10,
        30,
    )  # (connect_timeout, read_timeout)
    MAX_RETRIES: ClassVar[int] = 3
    BACKOFF_FACTOR: ClassVar[float] = 0.3
    RETRY_STATUS_CODES: ClassVar[list[int]] = [500, 502, 503, 504, 429]
    CHUNK_SIZE: ClassVar[int] = 8192  # For streaming downloads


def create_robust_session() -> requests.Session:
    """Create a requests session with retry strategy and timeout config."""
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=NetworkConfig.MAX_RETRIES,
        status_forcelist=NetworkConfig.RETRY_STATUS_CODES,
        backoff_factor=NetworkConfig.BACKOFF_FACTOR,
        raise_on_redirect=False,
        raise_on_status=False,
    )

    # Mount adapter with retry strategy
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set default headers
    session.headers.update(
        {
            'User-Agent': 'CAMEL-AI Document Processor/1.0',
            'Accept': 'application/pdf,*/*',
            'Connection': 'keep-alive',
        }
    )

    return session


def download_file_with_progress(
    session: requests.Session,
    url: str,
    file_path: Path,
    max_size_mb: int = 100,
) -> bool:
    """
    Download a file with progress indication and size limits.

    Args:
        session: Configured requests session
        url: URL to download from
        file_path: Local path to save the file
        max_size_mb: Maximum file size in MB

    Returns:
        bool: True if download successful, False otherwise
    """
    try:
        logger.info(f"Starting download: {url}")

        # Make request with streaming
        response = session.get(
            url,
            timeout=NetworkConfig.TIMEOUT,
            stream=True,
            allow_redirects=True,
        )
        response.raise_for_status()

        # Check content length
        content_length = response.headers.get('content-length')
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            if size_mb > max_size_mb:
                logger.warning(
                    f"File too large ({size_mb:.1f}MB > {max_size_mb}MB): "
                    f"{url}"
                )
                return False
            logger.info(f"File size: {size_mb:.1f}MB")

        # Download with progress
        downloaded_size = 0
        max_bytes = max_size_mb * 1024 * 1024

        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(
                chunk_size=NetworkConfig.CHUNK_SIZE
            ):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)
                    downloaded_size += len(chunk)

                    # Check size limit during download
                    if downloaded_size > max_bytes:
                        logger.warning(f"Download size limit exceeded: {url}")
                        file_path.unlink()  # Remove partial file
                        return False

        logger.info(
            f"Successfully downloaded: {file_path.name} "
            f"({downloaded_size:,} bytes)"
        )
        return True

    # Handle specific request exceptions first (most specific to general)
    except Timeout:
        logger.error(f"Timeout downloading {url}")
    except HTTPError as e:
        logger.error(
            f"HTTP error {e.response.status_code} downloading {url}: {e}"
        )
    except ConnectionError:
        logger.error(f"Connection error downloading {url}")
    except RequestException as e:
        # This catches other requests-related exceptions
        logger.error(f"Request error downloading {url}: {e}")
    except OSError as e:
        # File system errors (disk space, permissions, etc.)
        # This is separate from requests exceptions
        logger.error(f"File system error saving {file_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {e}")

    # Clean up partial file on error
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass

    return False


def download_files_robust(
    urls_filenames: dict,
    download_dir: Path,
) -> dict[str, bool]:
    """
    Download files with robust error handling and retry logic.

    Args:
        urls_filenames: Dict mapping URLs to filenames
        download_dir: Directory to save files

    Returns:
        dict: Mapping of filenames to success status
    """
    download_dir.mkdir(exist_ok=True, parents=True)
    results = {}

    with create_robust_session() as session:
        for url, filename in urls_filenames.items():
            file_path = download_dir / filename

            # Skip if file already exists and is valid
            if file_path.exists() and file_path.stat().st_size > 0:
                logger.info(f"File already exists: {filename}")
                results[filename] = True
                continue

            # Attempt download with exponential backoff
            success = False
            for attempt in range(1, NetworkConfig.MAX_RETRIES + 1):
                if attempt > 1:
                    wait_time = NetworkConfig.BACKOFF_FACTOR * (
                        2 ** (attempt - 1)
                    )
                    logger.info(
                        f"Retrying in {wait_time:.1f}s... "
                        f"(attempt {attempt})"
                    )
                    time.sleep(wait_time)

                success = download_file_with_progress(session, url, file_path)
                if success:
                    break

            results[filename] = success
            if not success:
                logger.error(
                    f"Failed to download after "
                    f"{NetworkConfig.MAX_RETRIES} attempts: {url}"
                )

    return results


def create_zip_file_safe(
    files: dict,
    download_dir: Path,
    zip_name: str,
    download_results: dict[str, bool],
) -> Optional[Path]:
    """
    Create a zip file containing only successfully downloaded files.

    Args:
        files: Dict mapping URLs to filenames
        download_dir: Directory containing files
        zip_name: Name of zip file to create
        download_results: Results from download attempt

    Returns:
        Optional[Path]: Path to zip file if created successfully,
                       None otherwise
    """
    zip_path = download_dir / zip_name
    successful_files = []

    # Check which files were successfully downloaded
    for filename in files.values():
        if download_results.get(filename, False):
            file_path = download_dir / filename
            if file_path.exists() and file_path.stat().st_size > 0:
                successful_files.append(filename)

    if not successful_files:
        logger.error("No files available to create zip")
        return None

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for filename in successful_files:
                file_path = download_dir / filename
                zipf.write(file_path, arcname=filename)
                logger.info(f"Added to zip: {filename}")

        logger.info(f"Successfully created zip: {zip_path}")
        return zip_path

    except zipfile.BadZipFile as e:
        logger.error(f"Zip file error: {e}")
        if zip_path.exists():
            zip_path.unlink()
        return None
    except OSError as e:
        logger.error(f"File system error creating zip: {e}")
        if zip_path.exists():
            zip_path.unlink()
        return None


def handle_agent_request_safely(
    agent: ChatAgent, request: str, max_retries: int = 2
) -> str:
    """
    Handle agent requests with retry logic for network-related failures.

    Args:
        agent: ChatAgent instance
        request: Request string
        max_retries: Maximum number of retries

    Returns:
        str: Agent response or error message
    """
    for attempt in range(max_retries + 1):
        try:
            response = agent.step(request)
            content = response.msgs[0].content

            # Handle potential None content
            if content is None:
                logger.warning(
                    f"Agent returned None content (attempt {attempt + 1})"
                )
                if attempt == max_retries:
                    return "Agent returned empty response after all attempts"
                continue

            return content

        except IndexError:
            logger.warning(
                f"Agent response has no messages (attempt {attempt + 1})"
            )
            if attempt == max_retries:
                return "Agent response contained no messages"

        except Exception as e:
            logger.warning(
                f"Agent request failed (attempt {attempt + 1}): {e}"
            )
            if attempt == max_retries:
                return (
                    f"Agent request failed after {max_retries + 1} "
                    f"attempts: {e!s}"
                )

        # Brief pause before retry
        if attempt < max_retries:
            time.sleep(1)

    # This should never be reached, but included for completeness
    return "Unexpected error: no response after all attempts"


def main():
    """Main function with comprehensive error handling."""
    try:
        # Use temporary directory for cross-platform compatibility
        with tempfile.TemporaryDirectory() as temp_dir:
            download_dir = Path(temp_dir) / "test"
            logger.info(f"Using temporary directory: {download_dir}")
            print(f"\nTEMPORARY DIRECTORY: {download_dir}")
            print(f"PDFs will be downloaded to: {download_dir}")
            print(
                f"example.txt will be created at: "
                f"{download_dir / 'example.txt'}"
            )
            print(
                f"test.zip will be created at: "
                f"{download_dir / 'test.zip'}\n"
            )

            # Files to download
            files = {
                "https://arxiv.org/pdf/1512.03385.pdf": "1512.03385.pdf",
                "https://arxiv.org/pdf/1706.03762.pdf": "1706.03762.pdf",
            }

            # Download files with robust handling
            logger.info("Starting file downloads...")
            download_results = download_files_robust(files, download_dir)

            # Report download results
            successful_downloads = sum(download_results.values())
            total_downloads = len(download_results)
            logger.info(
                f"Download summary: {successful_downloads}/"
                f"{total_downloads} successful"
            )

            if successful_downloads == 0:
                logger.error("No files downloaded successfully. Exiting.")
                return

            # Create zip file with only successful downloads
            zip_path = create_zip_file_safe(
                files, download_dir, "test.zip", download_results
            )
            if not zip_path:
                logger.error("Failed to create zip file. Exiting.")
                return

            try:
                # Initialize agent & toolkit
                logger.info("Initializing AI agent...")
                doc_toolkit = DocumentToolkit()

                model = ModelFactory.create(
                    model_platform=ModelPlatformType.OPENAI,
                    model_type=ModelType.GPT_4O_MINI,
                    model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
                )

                agent = ChatAgent(
                    system_message=(
                        "You are a helpful assistant that can read "
                        "arbitrary documents. Use the provided "
                        "DocumentToolkit to extract text."
                    ),
                    model=model,
                    tools=[*doc_toolkit.get_tools()],
                )

                # Extract content from zip file
                logger.info("Processing documents with AI agent...")
                response = handle_agent_request_safely(
                    agent,
                    f"Extract content in the document located at "
                    f"{zip_path}, return the abstract of them.",
                )

                print("\n" + "=" * 50)
                print("DOCUMENT ANALYSIS RESULTS")
                print("=" * 50)
                print(response)

                # Demonstrate file operations
                example_file = download_dir / "example.txt"

                logger.info("Demonstrating file operations...")

                # Create file
                response = handle_agent_request_safely(
                    agent,
                    f"Create a new file named {example_file} and add "
                    f"content about camel-ai.",
                )
                print("\n" + "-" * 30)
                print("FILE CREATION:")
                print(response)

                if example_file.exists():
                    # File operations
                    operations = [
                        (
                            f"Insert the line 'Inserted by agent' at line 1 "
                            f"in the file {example_file}.",
                            "LINE INSERTION:",
                        ),
                        (
                            f"Replace the line 'Inserted by agent' with "
                            f"'Replaced by agent' in the file "
                            f"{example_file}.",
                            "LINE REPLACEMENT:",
                        ),
                        (
                            f"Read lines 1 to 3 from the file "
                            f"{example_file}.",
                            "FILE READING:",
                        ),
                    ]

                    for request, title in operations:
                        response = handle_agent_request_safely(agent, request)
                        print(f"\n{'-' * 30}")
                        print(f"{title}")
                        print(response)

            except Exception as e:
                logger.error(f"Error during AI processing: {e}")
                print(f"AI processing failed: {e}")

    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        print(f"Application failed: {e}")


if __name__ == "__main__":
    main()
