

from camel.models.reward import Evaluator, SkyworkRewardModel
from camel.types import ModelType

reward_model = SkyworkRewardModel(
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

threshoids = {"helpfulness": 1.5, "correctness": 1.5}
is_acceptable = evaluator.filter_data(messages, threshoids)
print("Is acceptable: ", is_acceptable)
'''
===============================================================================
Is acceptable:  True
===============================================================================
'''
