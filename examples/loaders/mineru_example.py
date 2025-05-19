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

from camel.loaders import MinerU


def main():
    # Initialize MinerU client
    mineru = MinerU()

    print("Example 1: Single URL extraction")
    try:
        # Extract content from a single URL
        response = mineru.extract_url(
            url="https://arxiv.org/pdf/2311.10993.pdf",
        )
        task_id = response['task_id']
        print(f"Task ID: {task_id}")

        # Wait for completion
        result = mineru.wait_for_completion(task_id)
        print("\nTask completed successfully:")
        print(f"Download URL: {result['full_zip_url']}")

    except Exception as e:
        print(f"Single URL extraction failed: {e}")

    print("\nExample 2: Batch URL extraction")
    try:
        # Prepare list of files for batch extraction
        files = [
            {
                "url": "https://arxiv.org/pdf/2311.10993.pdf",
                "is_ocr": True,
                "data_id": "doc1",
            },
            {
                "url": "https://arxiv.org/pdf/2310.07298.pdf",
                "is_ocr": True,
                "data_id": "doc2",
            },
        ]

        # Batch extract URLs
        batch_id = mineru.batch_extract_urls(
            files=files,
        )
        print(f"Batch ID: {batch_id}")

        # Wait for completion
        results = mineru.wait_for_completion(batch_id, is_batch=True)
        print("\nBatch processing completed successfully:")
        for result in results['extract_result']:
            print(f"\nDocument: {result['data_id']}")
            print(f"Filename: {result['file_name']}")
            print(f"Download URL: {result['full_zip_url']}")

    except Exception as e:
        print(f"Batch URL extraction failed: {e}")


if __name__ == "__main__":
    main()

"""
===============================================================================
Example output:

Example 1: Single URL extraction
Task ID: 6e7f4a49-edfa-443d-a78b-d5ad4be0a2bf

Task completed successfully:
Download URL: https://cdn-mineru.openxlab.org.cn/pdf/690a7956-eaaa-4fb2-ad7d-6056d1d4e316.zip

Example 2: Batch URL extraction
Batch ID: 3a473301-ce78-44cc-bdc0-c0070ea88bcd

Batch processing completed successfully:

Document: doc1
Filename: 2311.10993.pdf
Download URL: https://cdn-mineru.openxlab.org.cn/pdf/690a7956-eaaa-4fb2-ad7d-6056d1d4e316.zip

Document: doc2
Filename: 2310.07298.pdf
Download URL: https://cdn-mineru.openxlab.org.cn/pdf/250a3762-406e-4279-aa80-47e5ea934509.zip
===============================================================================
"""
