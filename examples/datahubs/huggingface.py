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
from camel.datahubs.huggingface import HuggingFaceDatasetManager
from camel.datahubs.models import Record

manager = HuggingFaceDatasetManager()

USERNAME = "username"
REPO_ID = f"{USERNAME}/test-dataset-example"

records = [
    Record(
        id="record-1",
        content={"input": "What is AI?", "output": "Artificial Intelligence"},
        metadata={"method": "SFT"},
    ),
    Record(
        id="record-2",
        content={"input": "Translate 'hello'", "output": "Bonjour"},
        metadata={"method": "GPT"},
    ),
]

# 1. create a dataset
print("Creating dataset...")
dataset_url = manager.create_dataset(name=REPO_ID)
print(f"Dataset created: {dataset_url}")

# 2. create a dataset card
print("Creating dataset card...")
manager.create_dataset_card(
    dataset_name=REPO_ID,
    description="Test dataset",
    license="mit",
    language=["en"],
    size_category="<1MB",
    version="0.1.0",
    tags=["test", "example"],
    task_categories=["other"],
    authors=["camel-ai"],
)
print("Dataset card created successfully.")

# 3. add records to the dataset
print("Adding records to the dataset...")
manager.add_records(dataset_name=REPO_ID, records=records)
print("Records added successfully.")

# 4. list all records
print("Listing all records...")
all_records = manager.list_records(dataset_name=REPO_ID)
print("Records in the dataset:")
for record in all_records:
    print(
        f"- ID: {record.id}, Input: {record.content['input']}, "
        f"Output: {record.content['output']}"
    )

# 5. update a record
new_records = [
    Record(
        id="record-3",
        content={"input": "What is ML?", "output": "Machine Learning"},
        metadata={"method": "Updated GPT"},
    )
]
print("Updating records...")
manager.update_records(dataset_name=REPO_ID, records=new_records)
print("Records updated successfully.")

# 6. list updated records
print("Listing updated records...")
updated_records = manager.list_records(dataset_name=REPO_ID)
print("Updated records in the dataset:")
for record in updated_records:
    print(
        f"- ID: {record.id}, Input: {record.content['input']}, "
        f"Output: {record.content['output']}"
    )

# 7. delete a record
print("Deleting record with ID 'record-1'...")
manager.delete_record(dataset_name=REPO_ID, record_id="record-1")
print("Record deleted successfully.")

# 8. list records after deletion
print("Listing records after deletion...")
final_records = manager.list_records(dataset_name=REPO_ID)
print("Final records in the dataset:")
for record in final_records:
    print(
        f"- ID: {record.id}, Input: {record.content['input']}, "
        f"Output: {record.content['output']}"
    )

# 9. list all datasets
print("Listing all datasets...")
datasets = manager.list_datasets(USERNAME)
print("Datasets:")
for dataset in datasets:
    print(f"- {dataset}")

# 10. delete a dataset
print(f"Deleting dataset: {REPO_ID}...")
manager.delete_dataset(dataset_name=REPO_ID)
print("Dataset deleted successfully.")
