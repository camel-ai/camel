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

from collections import defaultdict
import logging
import os
import json
import math
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

def setup_logger():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    log_filename = f'logs/omega_data_gene_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

logger = setup_logger()
load_dotenv()

class State:
    """表示推理过程中的一个状态"""
    def __init__(self, solution_prefix: str, parent: Optional['State'] = None):
        self.solution_prefix = solution_prefix
        self.parent = parent
        self.children = []
        self.visits = 0  # N(s)
        self.value = 0.0  # V(s)
        self.mc_value = 0.0  # MC(s)

class SearchTree:
    """管理推理过程的搜索树"""
    def __init__(self):
        self.root = None
        self.nodes = []

    def add_state(self, state: State):
        if not self.root:
            self.root = state
        self.nodes.append(state)
        if state.parent:
            state.parent.children.append(state)

class OmegaDataGene:
    def __init__(self, chat_agent, golden_answers=None, 
                 c_puct=0.5, alpha=0.5, beta=0.9,
                 max_steps=20, num_rollouts=16, rollout_budget=200):
        """
        初始化改进版数据生成器
        
        Args:
            chat_agent: 对话代理
            golden_answers: 标准答案字典
            c_puct: 探索常数
            alpha: MC(s)的权重
            beta: 长度惩罚因子
            max_steps: 最大搜索步数
            num_rollouts: 每次蒙特卡洛模拟的次数
            rollout_budget: 总rollout预算
        """
        self.chat_agent = chat_agent
        self.golden_answers = golden_answers if golden_answers else {}
        self.c_puct = c_puct
        self.alpha = alpha
        self.beta = beta
        self.max_steps = max_steps
        self.num_rollouts = num_rollouts
        self.rollout_budget = rollout_budget
        
        self.search_tree = SearchTree()
        self.total_rollouts = 0
        logger.info("OmegaDataGene initialized with parameters: "
                   f"c_puct={c_puct}, alpha={alpha}, beta={beta}")

    def get_rollout(self, state: State) -> str:
        """生成一个推理路径"""
        prompt = f"""Please continue the solution based on these steps:
        {state.solution_prefix}
        
        Requirements:
        1. Continue from the existing steps
        2. Add detailed reasoning for each new step
        3. Ensure logical flow with previous steps
        4. Provide clear conclusions
        """
        response = self.chat_agent.step(prompt)
        return response.msgs[0].content

    def monte_carlo_estimation(self, state: State) -> float:
        """
        执行蒙特卡洛估计，评估当前状态的质量
        返回正确rollout的比例
        """
        correct_count = 0
        for _ in range(self.num_rollouts):
            if self.total_rollouts >= self.rollout_budget:
                break
            
            rollout = self.get_rollout(state)
            is_correct = self.verify_answer(state.solution_prefix + rollout)
            if is_correct:
                correct_count += 1
            self.total_rollouts += 1
            
        return correct_count / self.num_rollouts

    def compute_score(self, state: State, rollout: str) -> float:
        """
        计算状态-推理路径对的分数
        Score(s,r) = Q(s,r) + U(s)
        """
        # 计算Q值：Q(s,r) = α^(1-MC(s)) * β^(len(r)/L)
        q_value = (self.alpha ** (1 - state.mc_value)) * \
                 (self.beta ** (len(rollout.split()) / 500))
        
        # 计算U值：U(s) = c_puct * sqrt(sum(N(s'))) / (1 + N(s))
        total_visits = sum(node.visits for node in self.search_tree.nodes)
        u_value = self.c_puct * math.sqrt(total_visits) / (1 + state.visits)
        
        return q_value + u_value

    def verify_answer(self, solution: str) -> bool:
        """验证答案是否正确"""
        if not self.golden_answers:
            return False
        
        prompt = f"""Verify if this solution is correct:
        Solution: {solution}
        Expected: {self.golden_answers}
        Return True or False only.
        """
        response = self.chat_agent.step(prompt)
        return response.msgs[0].content.strip().lower() == "true"

    def binary_search_expansion(self, state: State, rollout: str):
        """使用二分搜索找到错误的推理步骤"""
        steps = rollout.split('\n')
        left, right = 0, len(steps)
        
        while left < right:
            mid = (left + right) // 2
            partial_rollout = '\n'.join(steps[:mid])
            if self.verify_answer(state.solution_prefix + partial_rollout):
                left = mid + 1
            else:
                right = mid
        
        # 创建新状态，包含正确部分
        if left > 0:
            correct_part = '\n'.join(steps[:left-1])
            new_state = State(state.solution_prefix + correct_part, parent=state)
            self.search_tree.add_state(new_state)
            return new_state
        return state

    def solve(self, question: str) -> str:
        """
        使用改进的搜索算法解决问题
        """
        logger.info(f"Starting to solve question: {question}")
        
        # 初始化根状态
        root_state = State(question)
        self.search_tree.root = root_state
        self.search_tree.nodes = [root_state]
        
        current_state = root_state
        step_count = 0
        
        while step_count < self.max_steps:
            # 1. 蒙特卡洛估计
            current_state.mc_value = self.monte_carlo_estimation(current_state)
            
            # 2. 生成新的推理路径
            rollout = self.get_rollout(current_state)
            
            # 3. 验证答案
            if self.verify_answer(current_state.solution_prefix + rollout):
                logger.info("Found correct solution!")
                return current_state.solution_prefix + rollout
            
            # 4. 二分搜索扩展
            current_state = self.binary_search_expansion(current_state, rollout)
            current_state.visits += 1
            step_count += 1
            
            logger.info(f"Step {step_count}: MC value = {current_state.mc_value}")
        
        # 返回最佳路径
        best_state = max(self.search_tree.nodes, 
                        key=lambda s: s.mc_value)
        return best_state.solution_prefix

    def export_solutions(self, filepath='solutions.json'):
        """导出解决方案"""
        export_data = {
            "solutions": [{
                "state": node.solution_prefix,
                "mc_value": node.mc_value,
                "visits": node.visits,
                "has_parent": bool(node.parent),
                "num_children": len(node.children)
            } for node in self.search_tree.nodes],
            "total_rollouts": self.total_rollouts,
            "export_time": datetime.now().isoformat()
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Solutions exported successfully to {filepath}")
        except Exception as e:
            logger.error(f"Error exporting solutions: {str(e)}")
