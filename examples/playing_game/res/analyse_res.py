import json
from collections import Counter

with open("chat_log(3.5-3.5).json", "r") as file:
    chat_log = json.load(file)

ori_res = chat_log["option_res"]
res = list(zip(ori_res["Player 1"], ori_res["Player 2"]))
count = Counter(res)
print(count)
