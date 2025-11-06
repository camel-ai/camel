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

from camel.loaders import ChunkrReader, ChunkrReaderConfig


async def process_file(
    chunkr: ChunkrReader,
    file_path: str,
    chunk_config: ChunkrReaderConfig = None,
) -> str:
    try:
        task_id = await chunkr.submit_task(
            file_path,
            chunkr_config=chunk_config,
        )
        result = await chunkr.get_task_output(task_id)
        return result
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")


def read_with_different_model():
    r"""Reads a document using the Chunkr API."""

    chunk_config = ChunkrReaderConfig()

    print("Whether to use high-resolution images for processing the file:")
    print("1. Yes")
    print("2. No")
    choice = input("Enter your choice (1-2): ")
    high_resolution_strategies = {"1": "Yes", "2": "No"}

    if choice not in high_resolution_strategies:
        print("Invalid choice. Exiting.")
        return

    is_high_resolution = high_resolution_strategies[choice]
    chunk_config.high_resolution = is_high_resolution == "Yes"

    print("Choose an OCR strategy:")
    print("1. Auto")
    print("2. All")
    ocr_choice = input("Enter your choice (1-2) [Default: All]: ")
    ocr_strategies = {"1": "Auto", "2": "All"}

    if ocr_choice not in ocr_strategies:
        chunk_config.ocr_strategy = "All"
    else:
        chunk_config.ocr_strategy = ocr_strategies[ocr_choice]

    while True:
        target_chunk_length = (
            input(
                "Enter The target number of words in each chunk."
                "[Default: 512]: "
            )
            or "512"
        )
        if target_chunk_length.isdigit() and int(target_chunk_length) > 0:
            chunk_config.chunk_processing = int(target_chunk_length)
            break
        else:
            print("Invalid input. Please enter a valid positive integer.")

    file_path = input("Please provide the file path: ")

    chunkr_reader = ChunkrReader()

    try:
        result = asyncio.run(
            process_file(chunkr_reader, file_path, chunk_config)
        )
        print(result)
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    read_with_different_model()
