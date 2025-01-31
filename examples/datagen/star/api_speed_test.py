import time

from openai import OpenAI

client = OpenAI(
    api_key="fw_3ZZJeCFr4snH8syE8phgSyhq",
    base_url="https://api.fireworks.ai/inference/v1",
)

batch_start_time1 = time.time()
response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": (
                "answer my question in short and give your final answer within"
                " \\boxed{}."
            ),
        },
        {
            "role": "user",
            "content": (
                "Find the number of integers $c$ such that the equation"
                " \\[\\left||20|x|-x^2|-c\\right|=21\\]has $12$ distinct"
                " real solutions.",
            ),
        },
    ],
    # notice the change in the model name
    model="accounts/fireworks/models/deepseek-r1",
    max_tokens=20480,
)

batch_start_time2 = time.time()

print(batch_start_time2 - batch_start_time1)

print(response.choices[0].message.content)
