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
from camel.models.reward import Evaluator, NemotronRewardModel
from camel.types import ModelType

reward_model = NemotronRewardModel(
    model_type=ModelType.NVIDIA_NEMOTRON_340B_REWARD,
    url="https://integrate.api.nvidia.com/v1",
)

evaluator = Evaluator(reward_model=reward_model)

messages = [
    {"role": "user", "content": "I am going to Paris, what should I see?"},
    {
        "role": "assistant",
        "content": "Ah, Paris, the City of Light! There are so many amazing "
        "things to see and do in this beautiful city ...",
    },
]

scores = evaluator.evaluate(messages)
print("Scores: ", scores)
'''
===============================================================================
Scores:  {'helpfulness': 1.6171875, 'correctness': 1.6484375, 'coherence': 3.
3125, 'complexity': 0.546875, 'verbosity': 0.515625}
===============================================================================
'''

scores_types = reward_model.get_scores_types()
print("Types: ", scores_types)
'''
===============================================================================
Types:  ['helpfulness', 'correctness', 'coherence', 'complexity', 'verbosity']
===============================================================================
'''

thresholds = {"helpfulness": 1.5, "correctness": 1.5}
is_acceptable = evaluator.filter_data(messages, thresholds)
print("Is acceptable: ", is_acceptable)
'''
===============================================================================
Is acceptable:  True
===============================================================================
'''
