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
import os
from pathlib import Path

from camel.datasets.medicine import MedicalDataset, MedicalDataPoint, load_json_data

# Get the current directory path
current_dir = Path(os.path.dirname(os.path.abspath(__file__)))

# Load example data from RDC.json
data_path = current_dir / "medicine_example_data" / "RDC.json"
print(f"Attempting to load data from: {data_path}")
sourcedata = load_json_data(str(data_path))

# Create medical dataset instance
dataset = MedicalDataset(data=sourcedata)

async def main():
    r"""Main async function to demonstrate dataset usage.
    
    Initializes the dataset, displays its size, and samples a random data point
    to demonstrate basic functionality.
    """
    # Initialize the dataset
    await dataset.setup()
    
    # Check dataset statistics
    print(f"Dataset size: {len(dataset)}")
    if len(dataset) > 0:
        # Sample and display a random data point
        sampled_datapoint = dataset.sample()
        print("Randomly sampled data point:")
        print(sampled_datapoint)
    else:
        print("Dataset is empty, cannot sample data points")

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())