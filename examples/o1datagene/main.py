import os
import logging
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from camel.agents import ChatAgent
import json

# 配置日志
def setup_logger():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    log_filename = f'logs/omega_prm_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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

# 加载环境变量
load_dotenv()
logger.info("Environment variables loaded")

# 初始化 AI 模型
sys_msg = 'You are a genius at slow-thinking data and code'

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="deepseek-chat",
    api_key=os.environ.get("OPENAI_COMPATIBILIY_API_KEY"),
    url=os.environ.get("OPENAI_COMPATIBILIY_API_BASE_URL"),
    model_config_dict={"temperature": 0.4, "max_tokens": 4096},
)

chat_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    message_window_size=10,
)

class O1DataGene:
    def __init__(self, chat_agent, golden_answers=None, search_limit=100):
        self.chat_agent = chat_agent
        self.golden_answers = golden_answers if golden_answers else {}
        self.search_limit = search_limit
        self.solution_tree = defaultdict(dict)  # 存储正确的解决步骤
        logger.info("O1DataGene initialized with search_limit=%d", search_limit)

    def get_answer(self, question, context=""):
        """
        获取 AI 的思考过程和答案
        """
        prompt = f"""请一步一步思考并解决这个问题：{question}
        已有内容：{context}
        要求：
        1. 分析问题要求
        2. 列出解题步骤
        3. 执行解题过程
        4. 给出最终答案
        请详细说明每一步的思考过程。
        """
        
        response = self.chat_agent.step(prompt)
        answer = response.msgs[0].content
        logger.info("AI思考过程:\n%s", answer)
        return answer

    def verify_answer(self, question, answer):
        """
        验证答案是否正确
        """
        prompt = f"""请判断以下两个答案是否表达相同的含义：
        问题：{question}
        答案1：{answer}
        答案2：{self.golden_answers[question]}
        只需要回答 "True" 或 "False"。
        """
        
        response = self.chat_agent.step(prompt)
        is_correct = response.msgs[0].content.strip().lower() == "true"
        logger.info("答案验证结果: %s", is_correct)
        return is_correct

    def monte_carlo_tree_search(self, question, partial_solution=""):
        """
        使用蒙特卡洛树搜索生成和验证答案
        """
        logger.info("开始蒙特卡洛树搜索")
        best_solution = None
        best_score = 0
        
        for i in range(self.search_limit):
            # 生成新的答案
            current_solution = self.get_answer(question, partial_solution)
            
            # 验证答案
            is_correct = self.verify_answer(question, current_solution)
            
            if is_correct:
                logger.info("找到正确答案！停止搜索")
                return current_solution, True
            
            # 分析错误，获取相似度评分
            prompt = f"""分析这个答案与正确答案的相似度（0-1之间）：
            问题：{question}
            生成答案：{current_solution}
            正确答案：{self.golden_answers[question]}
            只需要返回一个0-1之间的数字。
            """
            response = self.chat_agent.step(prompt)
            try:
                score = float(response.msgs[0].content.strip())
                if score > best_score:
                    best_score = score
                    best_solution = current_solution
                logger.info("当前搜索进度: %d/%d, 最佳分数: %.2f", i+1, self.search_limit, best_score)
            except ValueError:
                continue
                
        return best_solution, False

    def binary_search_error(self, question, solution):
        """
        使用二分查找定位第一个错误
        """
        logger.info("开始二分查找错误位置")
        sentences = solution.split('。')
        left, right = 0, len(sentences)
        
        while left < right:
            mid = (left + right) // 2
            partial_solution = '。'.join(sentences[:mid]) + '。'
            logger.info("检查解答片段:\n%s", partial_solution)
            
            # 验证当前部分是否正确
            is_correct = self.verify_answer(question, partial_solution)
            
            if is_correct:
                left = mid + 1
            else:
                right = mid
                
        error_position = left
        logger.info("找到第一个错误位置: 第%d句", error_position)
        return error_position

    def solve(self, question):
        """
        解决问题的主要流程
        """
        logger.info("\n=== 开始解决问题: %s ===", question)
        
        # 1. 使用蒙特卡洛树搜索生成答案
        solution, is_correct = self.monte_carlo_tree_search(question)
        
        if is_correct:
            logger.info("问题已解决！")
            self.solution_tree[question] = {
                "solution": solution,
                "is_correct": True,
                "timestamp": datetime.now().isoformat()
            }
            return solution
            
        # 2. 如果答案不完全正确，使用二分查找定位错误
        error_pos = self.binary_search_error(question, solution)
        
        # 3. 存储正确部分
        correct_part = '。'.join(solution.split('。')[:error_pos]) + '。'
        final_solution = self.get_answer(question, correct_part)
        self.solution_tree[question] = {
            "solution": final_solution,
            "partial_correct": correct_part,
            "error_position": error_pos,
            "is_correct": False,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("最终答案:\n%s", final_solution)
        return final_solution

    def import_qa_from_json(self, json_file_path):
        """
        从JSON文件导入问题和答案数据
        JSON格式应为: {"question1": "answer1", "question2": "answer2", ...}
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                qa_data = json.load(f)
            
            # 更新golden_answers
            self.golden_answers.update(qa_data)
            logger.info(f"Successfully imported {len(qa_data)} QA pairs from {json_file_path}")
            return True
        except Exception as e:
            logger.error(f"Error importing JSON data: {str(e)}")
            return False

    def export_solutions(self, filepath='solutions.json'):
        """
        将解题过程和结果导出为JSON文件
        """
        export_data = {
            "solutions": self.solution_tree,
            "golden_answers": self.golden_answers,
            "export_time": datetime.now().isoformat()
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Solutions exported successfully to {filepath}")
        except Exception as e:
            logger.error(f"Error exporting solutions: {str(e)}")

# 示例使用
# golden_answers = {
#     "how many r in strawberry?": "3",
# }

# solver = O1DataGene(chat_agent, golden_answers)
# question = "how many r in strawberry?"
# solver.solve(question)
