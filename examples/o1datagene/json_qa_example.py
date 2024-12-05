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

import json
from main import O1DataGene, chat_agent
from datetime import datetime

def load_qa_data(file_path):
    """加载问答数据从JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)



# 加载JSON数据
qa_data = load_qa_data('qa_data.json')

# 创建O1DataGene实例
omega = O1DataGene(chat_agent, golden_answers=qa_data)

# 记录生成的答案
generated_answers = {}

# 测试问答
for question in qa_data.keys():
    print(f"\n问题: {question}")
    
    # 获取AI的思考过程和答案
    answer = omega.get_answer(question)
    generated_answers[question] = answer
    print(f"AI的思考过程和答案:\n{answer}")
    
    # 验证答案
    is_correct = omega.verify_answer(question, answer)
    print(f"答案验证结果: {'正确' if is_correct else '不正确'}")
    print("-" * 50)

# 导出所有包含问题和思考过程的答案数据


simplified_output = {
    'timestamp': datetime.now().isoformat(),
    'qa_pairs': generated_answers
}
simplified_file = f'generated_answers_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
with open(simplified_file, 'w', encoding='utf-8') as f:
    json.dump(simplified_output, f, ensure_ascii=False, indent=2)
print(f"生成的答案已导出到: {simplified_file}")
