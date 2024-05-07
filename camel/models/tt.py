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

# from groq import Groq
# from camel.types import ModelType
# from camel.types import (
#     ChatCompletion,
#     ChatCompletionMessage,
#     Choice,
#     CompletionUsage,
#     ModelType,
# )
# from typing import List


# ans = Groq(api_key="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").chat.completions.create(
#             messages=[{"role": "user", "content": "hi"}],
#             model=ModelType.GROQ_LLAMA_3_8_B.value)

# print(ans)


# _choices = []
# for choice in ans.choices:
#     choice.message = ChatCompletionMessage(
#         role=choice.message.role,
#         content=choice.message.content,
#         tool_calls=choice.message.tool_calls,
#     )
#     _choice = Choice(**choice.__dict__)
#     _choices.append(_choice)
# ans.choices = _choices

# ans.usage = CompletionUsage(**ans.usage.__dict__)
# print("------------------------------------")
# print(ChatCompletion(**ans.__dict__))
