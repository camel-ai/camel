

from camel.models.reward import Evaluator, SkyworkRewardModel
from camel.types import ModelType

reward_model = SkyworkRewardModel(
    model_type="Skywork/Skywork-Reward-Gemma-2-27B-v0.2",
)

evaluator = Evaluator(reward_model=reward_model)

messages = [
    {"role": "user", "content": "Jane has 12 apples. She gives 4 apples to her"
    " friend Mark, then buys 1 more apple, and finally splits all her apples "
    "equally among herself and her 2 siblings. How many apples does each "
    "person get?"},
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

threshoids = {"Score": 0}
is_acceptable = evaluator.filter_data(messages, threshoids)
print("Is acceptable: ", is_acceptable)
'''
===============================================================================
Is acceptable:  True
===============================================================================
'''
