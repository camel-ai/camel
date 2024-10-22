# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

from camel.loaders import ChunkrReader


def read_with_different_model():
    r"""Reads a document using the Chunkr API."""
    print("Choose a model for processing the file:")
    print("1. Fast")
    print("2. HighQuality")
    choice = input("Enter your choice (1-2): ")
    models = {"1": "Fast", "2": "HighQuality"}

    if choice not in models:
        print("Invalid choice. Exiting.")
        return

    model = models[choice]

    print("Choose an OCR strategy:")
    print("1. Auto")
    print("2. All")
    print("3. Off")
    ocr_choice = input("Enter your choice (1-3) [Default: Auto]: ")
    ocr_strategies = {"1": "Auto", "2": "All", "3": "Off"}

    if ocr_choice not in ocr_strategies:
        ocr_strategy = "Auto"
    else:
        ocr_strategy = ocr_strategies[ocr_choice]

    while True:
        target_chunk_length = (
            input("Enter the target chunk length [Default: 512]: ") or "512"
        )
        if target_chunk_length.isdigit() and int(target_chunk_length) > 0:
            break
        else:
            print("Invalid input. Please enter a valid positive integer.")

    file_path = input("Please provide the file path: ")

    chunkr_reader = ChunkrReader()

    try:
        task_id = chunkr_reader.submit_task(
            file_path,
            model=model,
            ocr_strategy=ocr_strategy,
            target_chunk_length=target_chunk_length,
        )

        result = chunkr_reader.get_task_output(task_id)
        print(result)

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    read_with_different_model()