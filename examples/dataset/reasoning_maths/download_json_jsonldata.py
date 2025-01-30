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
import os

import requests


def download_file(url, save_path):
    r"""Download a single file and save it to the specified path.

    Args:
        url (str): URL address of the file to download.
        save_path (str): Path where the file will be saved.

    Raises:
        requests.exceptions.RequestException: If the download fails due to a
            network error or invalid URL.
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Check if the request was successful
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"File successfully saved: {save_path}")
    except requests.exceptions.RequestException as e:
        print(f"Download failed: {url}, Error: {e}")


def batch_download(urls, output_dir, file_extension="json"):
    r"""Batch download files from multiple URLs and save them to a directory.

    Args:
        urls (List[str]): List of URLs to download files from.
        output_dir (str): Directory where the downloaded files will be saved.
        file_extension (str, optional): File extension for
            the downloaded files.Defaults to "json".
            Can also be set to "jsonl" or other extensions.

    Notes:
        The output directory will be created if it does not exist.
        Files will be named sequentially as `file_1.<extension>`,
        `file_2.<extension>`, etc.
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    for i, url in enumerate(urls):
        # Construct the file name and save path
        file_name = f"file_{i + 1}.{file_extension}"
        save_path = os.path.join(output_dir, file_name)

        # Download the file
        print(f"Downloading: {url}")
        download_file(url, save_path)


# Example usage
if __name__ == "__main__":
    # Define the list of URLs to download
    urls = [
        "https://raw.githubusercontent.com/QwenLM/Qwen2.5-Math/refs/heads/main/evaluation/data/aime24/test.jsonl"
        "https://raw.githubusercontent.com/QwenLM/Qwen2.5-Math/refs/heads/main/evaluation/data/amc23/test.jsonl"
        "https://raw.githubusercontent.com/QwenLM/Qwen2.5-Math/refs/heads/main/evaluation/data/college_math/test.jsonl"
        "https://raw.githubusercontent.com/QwenLM/Qwen2.5-Math/refs/heads/main/evaluation/data/gsm8k/train.jsonl"
        "https://raw.githubusercontent.com/QwenLM/Qwen2.5-Math/refs/heads/main/evaluation/data/gsm8k/test.jsonl"
        "https://raw.githubusercontent.com/QwenLM/Qwen2.5-Math/refs/heads/main/evaluation/data/gaokao2023en/test.jsonl"
    ]

    # Output directory
    output_directory = "./downloadeddata_files"

    # Batch download
    batch_download(urls, output_directory, file_extension="json")
