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

import time

from camel.loaders import MinerU

print("Example 1: Single URL extraction")
try:
    # Initialize MinerU client
    mineru = MinerU()

    # Extract content from a single URL
    response = mineru.extract_url(
        url="https://arxiv.org/pdf/2311.10993.pdf",
        is_ocr=True,
        enable_formula=True,
        enable_table=True,
        layout_model="doclayout_yolo",
        language="en",
    )
    task_id = response['task_id']  # Extract task_id from response
    print(f"Task ID: {task_id}")

    # Wait and check task status multiple times
    max_retries = 3
    for i in range(max_retries):
        try:
            status = mineru.get_task_status(task_id)
            print(f"\nTask Status (Attempt {i+1}):")
            print(status)

            if status.get('state') == 'done':
                break
            elif status.get('state') == 'failed':
                print(f"Task failed: {status.get('err_msg')}")
                break

            # Wait before next check
            time.sleep(5)
        except Exception as e:
            print(f"Error checking status: {e}")
            time.sleep(5)

except Exception as e:
    print(f"Single URL extraction failed: {e}")

"""
Example 1: Single URL extraction
Task ID: 8a1c76d6-de95-4b19-a185-f689090a4f29

Task Status (Attempt 1):
{
    'task_id': '8a1c76d6-de95-4b19-a185-f689090a4f29',
    'state': 'pending',
    'err_msg': ''
}

Task Status (Attempt 2):
{
    'task_id': '8a1c76d6-de95-4b19-a185-f689090a4f29', 
    'state': 'done',
    'err_msg': '',
    'full_zip_url': 
    'https://cdn-mineru.openxlab.org.cn/pdf/690a7956-eaaa-4fb2-ad7d-6056d1d4e316.zip'
}
"""

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
        enable_formula=True,
        enable_table=True,
        layout_model="doclayout_yolo",
        language="en",
    )
    print(f"Batch ID: {batch_id}")

    # Wait and check batch status multiple times
    max_retries = 3
    for i in range(max_retries):
        try:
            batch_status = mineru.get_batch_status(batch_id)
            print(f"\nBatch Status (Attempt {i+1}):")
            print(batch_status)

            # Check if all files are processed
            all_done = True
            for result in batch_status.get('extract_result', []):
                if result.get('state') not in ['done', 'failed']:
                    all_done = False
                    break

            if all_done:
                break

            # Wait before next check
            time.sleep(5)
        except Exception as e:
            print(f"Error checking batch status: {e}")
            time.sleep(5)

except Exception as e:
    print(f"Batch URL extraction failed: {e}")

"""
Example 2: Batch URL extraction

Output:
    Batch ID: a1cefd67-37c4-4827-b30f-31a42dc2fc80

    Batch Status (Attempt 1):
    {
        'batch_id': 'a1cefd67-37c4-4827-b30f-31a42dc2fc80',
        'extract_result': [
            {
                'data_id': 'doc1',
                'file_name': '2311.10993.pdf', 
                'state': 'pending',
                'err_msg': ''
            },
            {
                'data_id': 'doc2',
                'file_name': '2310.07298.pdf',
                'state': 'pending', 
                'err_msg': ''
            }
        ]
    }

    Batch Status (Attempt 2):
    {
        'batch_id': 'a1cefd67-37c4-4827-b30f-31a42dc2fc80',
        'extract_result': [
            {
                'data_id': 'doc1',
                'file_name': '2311.10993.pdf', 
                'state': 'done',
                'err_msg': '',
                'full_zip_url': 'https://cdn-mineru.openxlab.org.cn/pdf/690a7956-eaaa-4fb2-ad7d-6056d1d4e316.zip'
            },
            {
                'data_id': 'doc2',
                'file_name': '2310.07298.pdf',
                'state': 'done', 
                'err_msg': '',
                'full_zip_url': 'https://cdn-mineru.openxlab.org.cn/pdf/250a3762-406e-4279-aa80-47e5ea934509.zip'
            }
        ]
    }
"""
