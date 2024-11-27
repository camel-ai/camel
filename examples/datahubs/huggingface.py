# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
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
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import logging

from camel.datahubs.clients.huggingface import HuggingFaceDatasetManager
from camel.datahubs.models import Record

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


TOKEN = "your_huggingface_token"
DATASET_NAME = "username/example-dataset"

manager = HuggingFaceDatasetManager(token=TOKEN)

try:
    dataset_url = manager.create_dataset(
        name=DATASET_NAME, description="Example dataset for testing"
    )
    logger.info(f"Dataset created at: {dataset_url}")
except Exception as e:
    logger.error(f"Error creating dataset: {e}")

records_to_add = [
    Record(
        id="record-1",
        content={"input": "What is AI?", "output": "Artificial Intelligence"},
        metadata={"method": "SFT", "model_name": "gpt-4"},
    ),
    Record(
        id="record-2",
        content={"input": "Translate 'hello' to French", "output": "Bonjour"},
        metadata={"method": "GPT", "model_name": "gpt-3.5-turbo"},
    ),
]

try:
    manager.add_records(dataset_name=DATASET_NAME, records=records_to_add)
    logger.info("Records added successfully!")
except ValueError as e:
    logger.error(f"Error adding records: {e}")

records_to_update = [
    Record(
        id="record-2",
        content={"input": "Translate 'hello' to French", "output": "Salut"},
        metadata={"method": "Updated GPT", "model_name": "gpt-3.5-turbo"},
    ),
    Record(
        id="record-3",
        content={"input": "What is ML?", "output": "Machine Learning"},
        metadata={"method": "SFT", "model_name": "gpt-4"},
    ),
]

try:
    manager.update_records(
        dataset_name=DATASET_NAME, records=records_to_update
    )
    logger.info("Records updated successfully!")
except ValueError as e:
    logger.error(f"Error updating records: {e}")

try:
    records = manager.list_records(dataset_name=DATASET_NAME)
    logger.info("Current records in dataset:")
    for record in records:
        logger.info(record.model_dump())
except Exception as e:
    logger.error(f"Error listing records: {e}")
