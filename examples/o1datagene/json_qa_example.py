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

import json
from main import O1DataGene, chat_agent
from datetime import datetime

def load_qa_data(file_path):
    """Load Q&A data from a JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Load JSON data
qa_data = load_qa_data('qa_data.json')

# Create an instance of O1DataGene
omega = O1DataGene(chat_agent, golden_answers=qa_data)

# Record generated answers
generated_answers = {}

# Test Q&A
for question in qa_data.keys():
    print(f"\nQuestion: {question}")
    
    # Get AI's thought process and answer
    answer = omega.get_answer(question)
    generated_answers[question] = answer
    print(f"AI's thought process and answer:\n{answer}")
    
    # Verify the answer
    is_correct = omega.verify_answer(question, answer)
    print(f"Answer verification result: {'Correct' if is_correct else 'Incorrect'}")
    print("-" * 50)

# Export all data containing questions and thought processes

simplified_output = {
    'timestamp': datetime.now().isoformat(),
    'qa_pairs': generated_answers
}
simplified_file = f'generated_answers_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
with open(simplified_file, 'w', encoding='utf-8') as f:
    json.dump(simplified_output, f, ensure_ascii=False, indent=2)
print(f"The generated answers have been exported to: {simplified_file}")