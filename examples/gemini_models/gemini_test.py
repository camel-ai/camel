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

from camel.models import GeminiModel
from camel.types.enums import ModelType

#model1 use stream 
model = GeminiModel(ModelType.GEMINI_1_5_FLASH, {'stream' : True})
#model2 
# model = GeminiModel(ModelType.GEMINI_1_5_FLASH)
messages1 = [{'role':'user', 'parts': ['Tell me a story about basketball']}]
# messages2 = 'Tell me a story about basketball'

response = model.run(messages1)
if(model.stream):
    for chunk in response:
        print(chunk.text)
else:
    print(response.text)

token_count = model.token_counter.count_tokens_from_messages(messages1)
print(token_count)