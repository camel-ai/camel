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
from camel.models.reward import Evaluator, SkyworkRewardModel

reward_model = SkyworkRewardModel(
    model_type="Skywork/Skywork-Reward-Llama-3.1-8B-v0.2",
)

evaluator = Evaluator(reward_model=reward_model)

messages = [
    {
        "role": "user",
        "content": "Jane has 12 apples. She gives 4 apples to her friend Mark,"
        " then buys 1 more apple, and finally splits all her apples "
        "equally among herself and her 2 siblings. How many apples does each "
        "person get?",
    },
    {
        "role": "assistant",
        "content": "1. Jane starts with 12 apples and gives 4 to Mark. 12 - 4 "
        "= 8. Jane now has 8 apples.\n2. Jane buys 1 more apple. 8 + 1 = 9. "
        "Jane now has 9 apples.\n3. Jane splits the 9 apples equally among "
        "herself and her 2 siblings (3 people in total). 9 ÷ 3 = 3 apples "
        "each. Each person gets 3 apples.",
    },
]

scores = evaluator.evaluate(messages)
print("Scores: ", scores)
'''
===============================================================================
Scores:  {'Score': 13.6875}
===============================================================================
'''

scores_types = reward_model.get_scores_types()
print("Types: ", scores_types)
'''
===============================================================================
Types:  ['Score']
===============================================================================
'''

thresholds = {"Score": 0}
is_acceptable = evaluator.filter_data(messages, thresholds)
print("Is acceptable: ", is_acceptable)
'''
===============================================================================
Is acceptable:  True
===============================================================================
'''
