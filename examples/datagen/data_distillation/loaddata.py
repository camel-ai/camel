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
from datasets import load_dataset
import pandas as pd

# Load dataset
dataset = load_dataset("AI-MO/aimo-validation-aime")

# Convert the training set to a pandas DataFrame
df = pd.DataFrame(dataset['train'])

# Extract the 'problem' and 'answer' columns
problems_answers = df[['problem', 'answer']]

# Print results
print("\n=== Dataset Statistics ===")
print(f"Total samples: {len(problems_answers)}")
print("\n=== First 5 samples ===")
pd.set_option('display.max_colwidth', 100)  # Set display width
print(problems_answers.head())

# Save to CSV file (optional)
problems_answers.to_csv('problems_answers.csv', index=False, encoding='utf-8')
print("\nData has been saved to problems_answers.csv")