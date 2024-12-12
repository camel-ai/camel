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
# # O1DataGene with CAMEL
# ## experimental version

import os
from datetime import datetime
from dotenv import load_dotenv
import json
from camel.o1datagen.o1datagen import O1DataGene


# ### First we will set the OPENAI_API_KEY that will be used to generate the data.

# from getpass import getpass


# openai_api_key = getpass('Enter your OpenAI API key: ')
# os.environ["OPENAI_API_KEY"] = openai_api_key


# ### Create a system message to define agent's default role and behaviors.


sys_msg = 'You are a genius at slow-thinking data and code'


# ### Use ModelFactory to set up the backend model for agent, for more detailed model settings



from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


from camel.configs import DeepSeekConfig


# Define the model, here in this case we use gpt-4o-mini
# model = ModelFactory.create(
#     model_platform=ModelPlatformType.OPENAI,
#     model_type=ModelType.GPT_4O_MINI,
#     model_config_dict=ChatGPTConfig().as_dict(), # [Optional] the config for model
# )


"""
please set the below os environment:
export DEEPSEEK_API_KEY=""
"""
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEEPSEEK,
    model_type=ModelType.DEEPSEEK_CHAT,
    model_config_dict=DeepSeekConfig(temperature=1.3).as_dict(), # [Optional] the config for model
)

# Initialize AI model by OPENAI_COMPATIBLE_MODEL


# from camel.models import ModelFactory
# from camel.types import ModelPlatformType, ModelType

# from camel.configs import ChatGPTConfig

# sys_msg = 'You are a genius at slow-thinking data and code'
# model = ModelFactory.create(
#     model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
#     model_type="deepseek-chat",
#     api_key=os.environ.get("OPENAI_COMPATIBILIY_API_KEY"),
#     url=os.environ.get("OPENAI_COMPATIBILIY_API_BASE_URL"),
#     model_config_dict={"temperature": 0.4, "max_tokens": 4096},
# )


# ### Set ChatAgent



from camel.agents import ChatAgent
chat_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    message_window_size=10,
)


# ### Load Q&A data from a JSON file


def load_qa_data(file_path):
    """Load Q&A data from a JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)




# Load JSON data
qa_data = load_qa_data('qa_data.json')


# ### Create an instance of O1DataGene


# Create an instance of O1DataGene
testo1 = O1DataGene(chat_agent, golden_answers=qa_data)




# Record generated answers
generated_answers = {}


# ### Test Q&A



# Test Q&A
for question in qa_data.keys():
    print(f"\nQuestion: {question}")
    
    # Get AI's thought process and answer
    answer = testo1 .get_answer(question)
    generated_answers[question] = answer
    print(f"AI's thought process and answer:\n{answer}")
    
    # Verify the answer
    is_correct = testo1 .verify_answer(question, answer)
    print(f"Answer verification result: {'Correct' if is_correct else 'Incorrect'}")
    print("-" * 50)


# ### Export the generated answers to a JSON file
# 



simplified_output = {
    'timestamp': datetime.now().isoformat(),
    'qa_pairs': generated_answers
}
simplified_file = f'generated_answers_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
with open(simplified_file, 'w', encoding='utf-8') as f:
    json.dump(simplified_output, f, ensure_ascii=False, indent=2)
print(f"The generated answers have been exported to: {simplified_file}")

