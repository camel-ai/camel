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
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import FileWriteToolkit
from camel.types import ModelPlatformType

model = ModelFactory.create(
        model_platform=ModelPlatformType.QWEN,
        model_type="qwen-max",
        model_config_dict={"temperature": 0},
    )

sys_msg = "You are a helpful assistant"

output_dir = "./model_outputs"

tools_list = [
    *FileWriteToolkit(output_dir=output_dir).get_tools(),
]

# Initialize a ChatAgent with your custom tools
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools_list,
)

usr_query = "Please generate a simple Python script to analyze the word frequency in a text and save the code to a file. "

response = camel_agent.step(usr_query)
print(response.msgs[0].content)

'''
================================================================
I have generated a simple Python script for analyzing word frequency in a text, and the code has been saved to the file `word_frequency_analysis.py`. The script uses the `collections.Counter` class to count the frequency of each word after removing punctuation and converting the text to lowercase. It also includes a `main` function that demonstrates how to use the `word_frequency` function with a sample text.

Here is the content of the script:

```python
from collections import Counter

import re

def word_frequency(text):
    # Remove punctuation and make lowercase
    text = re.sub(r"\W", " ", text.lower())
    # Split into words
    words = text.split()
    # Count the frequency of each word
    freq = Counter(words)
    return freq

def main():
    test_text = "Hello world. Hello again, this is a simple text to analyze word frequency."
    print(word_frequency(test_text()))

if __name__ == "__main__":
    main()
================================================================
'''

print(response.info['tool_calls'])

'''
================================================================
[ToolCallingRecord(tool_name='write_to_file', args={'content': 
'from collections import Counter\n\nimport re\n\ndef 
word_frequency(text):\n    # Remove punctuation and make 
lowercase\n    text = re.sub(r"\\W", " ", text.lower())\n    
# Split into words\n    words = text.split()\n    # Count the 
frequency of each word\n    freq = Counter(words)\n    return 
freq\n\ndef main():\n    test_text = "Hello world. Hello again, 
this is a simple text to analyze word frequency."\n    
print(word_frequency(test_text))\n\nif __name__ == "__main__":
\n    main()', 'filename': 'word_frequency_analysis.py'}, 
result='Content successfully written to file: ./model_outputs
\\word_frequency_analysis.py', 
tool_call_id='call_2deb164ff8154bb493aae9')]
================================================================
'''

response_text = camel_agent.step("Please generate a paragraph that contains multiple occurrences of the word 'future' and save it.")
print("Agent response (text generation):", response_text.msgs[0].content)
# Agent response (text generation): The paragraph has been successfully generated and saved to a file named **future_paragraph.txt**.


response_replace = camel_agent.step(f"Replace 'future' with 'past' in the file future_paragraph.txt")
print("\nAgent response (replacement):", response_replace.msgs[0].content)
# Agent response (replacement): The word "future" has been successfully replaced with "past" in the file **future_paragraph.txt**.

