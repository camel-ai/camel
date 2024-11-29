import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import random
from tqdm import tqdm
import os
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.agents import ChatAgent
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ProcessorConfig:
    """数据处理配置类"""
    seed: int = 42  # 随机种子
    min_length: int = 50  # 最小文本长度
    max_length: int = 512  # 最大文本长度
    quality_threshold: float = 0.7  # 质量阈值
    complexity_threshold: float = 0.5  # 复杂度阈值
    dataset_size: int = 1000  # 目标数据集大小
    use_ai_model: bool = True  # 是否使用AI模型
    model_temperature: float = 0.4  # AI模型温度
    max_tokens: int = 4096  # AI模型最大token数


class AIModelHandler:
    """AI模型处理器"""

    def __init__(self, config: ProcessorConfig):
        self.config = config
        if config.use_ai_model:
            self.model = self._init_model()
            self.agent = self._init_agent()

    def _init_model(self):
        """初始化AI模型"""
        try:
            return ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
                model_type="deepseek-chat",
                api_key=os.environ.get("OPENAI_COMPATIBILIY_API_KEY"),
                url=os.environ.get("OPENAI_COMPATIBILIY_API_BASE_URL"),
                model_config_dict={
                    "temperature": self.config.model_temperature,
                    "max_tokens": self.config.max_tokens
                },
            )
        except Exception as e:
            logger.warning(f"AI模型初始化失败: {str(e)}")
            return None

    def _init_agent(self):
        """初始化AI代理"""
        if not self.model:
            return None

        system_message = """You are an expert at generating multi-hop question-answer pairs.
        For each context, you should:
        1. Identify multiple related facts or pieces of information
        2. Create questions that require reasoning across these multiple pieces
        3. Ensure the reasoning chain is clear and logical
        4. Generate questions that require at least 2-3 steps of reasoning
        5. Include the reasoning steps in the answer

        Format your response as:
        Question: [Complex question requiring multiple reasoning steps]
        Reasoning Steps:
        1. [First reasoning step]
        2. [Second reasoning step]
        3. [Final reasoning step]
        Answer: [Final answer]
        Supporting Facts: [List of relevant text segments used]
        """

        return ChatAgent(
            system_message=system_message,
            model=self.model,
            message_window_size=10
        )

    def generate_qa_pair(self, context: str,
                         related_contexts: List[str] = None) -> Optional[
        Dict[str, Any]]:
        """使用AI生成多跳问答对"""
        if not self.agent:
            return None

        try:
            # 构造包含多个相关上下文的提示
            context_prompt = f"Main Context: {context}\n"
            if related_contexts:
                context_prompt += "\nRelated Contexts:\n"
                for i, rel_ctx in enumerate(related_contexts, 1):
                    context_prompt += f"{i}. {rel_ctx}\n"

            prompt = f"""{context_prompt}
            Generate a multi-hop question-answer pair that requires reasoning across multiple pieces of information.
            The question should require at least 2-3 logical steps to answer.
            Include the reasoning steps and supporting facts in your response.

            Format your response as:
            Question: [your question]
            Reasoning Steps:
            1. [step 1]
            2. [step 2]
            3. [step 3]
            Answer: [your answer]
            Supporting Facts: [relevant text segments]
            """

            # 获取AI响应
            response = self.agent.step(prompt)
            content = response.msgs[0].content

            # 解析响应
            lines = content.strip().split('\n')
            question = None
            reasoning_steps = []
            answer = None
            supporting_facts = []

            current_section = None
            for line in lines:
                line = line.strip()
                if line.startswith('Question:'):
                    question = line[9:].strip()
                    current_section = 'question'
                elif line.startswith('Reasoning Steps:'):
                    current_section = 'reasoning'
                elif line.startswith('Answer:'):
                    answer = line[7:].strip()
                    current_section = 'answer'
                elif line.startswith('Supporting Facts:'):
                    current_section = 'facts'
                elif line and current_section == 'reasoning' and line[
                    0].isdigit():
                    reasoning_steps.append(line[2:].strip())
                elif line and current_section == 'facts':
                    supporting_facts.append(line)

            if question and answer and reasoning_steps:
                return {
                    'question': question,
                    'reasoning_steps': reasoning_steps,
                    'answer': answer,
                    'supporting_facts': supporting_facts,
                    'type': 'multi_hop_qa'
                }

        except Exception as e:
            logger.warning(f"AI生成多跳问答对时出错: {str(e)}")

        return None


class UserDataProcessor:
    """用户数据处理器"""

    def __init__(self, config: ProcessorConfig = None):
        self.config = config or ProcessorConfig()
        random.seed(self.config.seed)
        np.random.seed(self.config.seed)
        self.ai_handler = AIModelHandler(
            self.config) if self.config.use_ai_model else None

    def process_text(self, text: str, source: str = "user_input") -> List[
        Dict[str, Any]]:
        """处理单个文本"""
        # 将文本转换为标准格式
        raw_data = [{
            'text': text,
            'source': source,
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }]

        # 构造示例
        constructor = ExampleConstructor(self.config, self.ai_handler)
        examples = constructor.construct_examples(raw_data)

        # 数据管理
        curator = DataCurator(self.config)
        final_dataset = curator.curate_dataset(examples)

        return final_dataset

    def process_batch(self, texts: List[str], sources: List[str] = None) -> \
    List[Dict[str, Any]]:
        """批量处理多个文本"""
        if sources is None:
            sources = ["user_input"] * len(texts)
        elif len(sources) != len(texts):
            raise ValueError("sources列表长度必须与texts列表长度相同")

        raw_data = [
            {
                'text': text,
                'source': source,
                'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            for text, source in zip(texts, sources)
        ]

        # 构造示例
        constructor = ExampleConstructor(self.config, self.ai_handler)
        examples = constructor.construct_examples(raw_data)

        # 数据管理
        curator = DataCurator(self.config)
        final_dataset = curator.curate_dataset(examples)

        return final_dataset


class ExampleConstructor:
    """示例构造器"""

    def __init__(self, config: ProcessorConfig,
                 ai_handler: Optional[AIModelHandler] = None):
        self.config = config
        self.ai_handler = ai_handler

    def construct_examples(self, raw_data: List[Dict[str, Any]]) -> List[
        Dict[str, Any]]:
        """构造训练示例"""
        logger.info("开始构造训练示例...")
        examples = []

        for data in tqdm(raw_data, desc="构造示例"):
            try:
                # 1. 文本预处理
                processed_text = self._preprocess_text(data.get('text', ''))
                if not processed_text:
                    continue

                # 2. 生成关键信息对
                info_pairs = self._extract_info_pairs(processed_text)

                # 3. 构造问答对
                qa_pairs = self._generate_qa_pairs(info_pairs)

                # 4. 添加元数据
                example = {
                    'text': processed_text,
                    'qa_pairs': qa_pairs,
                    'metadata': {
                        'source': data.get('source', 'unknown'),
                        'timestamp': data.get('timestamp', ''),
                        'complexity': self._calculate_complexity(qa_pairs)
                    }
                }

                examples.append(example)

            except Exception as e:
                logger.warning(f"构造示例时出错: {str(e)}")
                continue

        logger.info(f"成功构造 {len(examples)} 个示例")
        return examples

    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        if not isinstance(text, str):
            return ''

        # 1. 基础清理
        text = text.strip()

        # 2. 长度检查
        if len(text) < self.config.min_length or len(
                text) > self.config.max_length:
            return ''

        # 3. 质量检查
        if not self._check_text_quality(text):
            return ''

        return text

    def _check_text_quality(self, text: str) -> bool:
        """检查文本质量"""
        # 1. 基本质量检查
        if text.count('.') < 2:  # 至少包含2个句子
            return False

        # 2. 特殊字符比例检查
        special_char_ratio = len(
            [c for c in text if not c.isalnum() and not c.isspace()]) / len(
            text)
        if special_char_ratio > 0.3:  # 特殊字符比例不超过30%
            return False

        return True

    def _extract_info_pairs(self, text: str) -> List[Dict[str, str]]:
        """提取信息对和关系"""
        # 分割成句子
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        info_pairs = []

        # 提取多个相关句子组合
        for i in range(len(sentences) - 2):
            if len(sentences[i]) > 10 and len(sentences[i + 1]) > 10:
                info_pairs.append({
                    'premise': sentences[i],
                    'intermediate': sentences[i + 1],
                    'conclusion': sentences[i + 2] if i + 2 < len(
                        sentences) else '',
                    'related_contexts': [
                                            s for j, s in enumerate(sentences)
                                            if j != i and j != i + 1 and len(
                            s) > 10
                                        ][:2]  # 最多取2个额外相关上下文
                })

        return info_pairs

    def _generate_qa_pairs(self, info_pairs: List[Dict[str, str]]) -> List[
        Dict[str, str]]:
        """生成多跳问答对"""
        qa_pairs = []

        for pair in info_pairs:
            # 1. 使用AI生成多跳问答对
            if self.ai_handler:
                # 构建完整上下文
                context = f"{pair['premise']}. {pair['intermediate']}. {pair['conclusion']}"
                ai_qa = self.ai_handler.generate_qa_pair(
                    context=context,
                    related_contexts=pair.get('related_contexts', [])
                )
                if ai_qa:
                    qa_pairs.append(ai_qa)
                    continue

            # 2. 如果AI生成失败，使用简单的模板生成
            # 注意：这只是后备方案，不能真正体现多跳问答的特点
            question = f"Based on the following information: {pair['premise']}, what can we conclude about {pair['conclusion']}?"
            answer = f"First, {pair['premise']}. Then, considering that {pair['intermediate']}, we can conclude that {pair['conclusion']}"

            qa_pairs.append({
                'question': question,
                'answer': answer,
                'reasoning_steps': [
                    f"Consider: {pair['premise']}",
                    f"Next, note that: {pair['intermediate']}",
                    f"Finally: {pair['conclusion']}"
                ],
                'supporting_facts': [
                    pair['premise'],
                    pair['intermediate'],
                    pair['conclusion']
                ],
                'type': 'template_generated_multi_hop'
            })

        return qa_pairs

    def _calculate_complexity(self, qa_pairs: List[Dict[str, Any]]) -> float:
        """计算问答对的复杂度"""
        if not qa_pairs:
            return 0.0

        # 基于多个因素计算复杂度
        complexities = []
        for qa in qa_pairs:
            # 1. 推理步骤数量
            reasoning_steps_count = len(qa.get('reasoning_steps', []))

            # 2. 支持事实数量
            supporting_facts_count = len(qa.get('supporting_facts', []))

            # 3. 问题长度
            question_length = len(qa['question'].split())

            # 4. 答案长度
            answer_length = len(qa['answer'].split())

            # 计算单个问答对的复杂度
            qa_complexity = (
                    min(reasoning_steps_count / 3, 1.0) * 0.4 +  # 推理步骤权重
                    min(supporting_facts_count / 3, 1.0) * 0.3 +  # 支持事实权重
                    min(question_length / 20, 1.0) * 0.15 +  # 问题长度权重
                    min(answer_length / 50, 1.0) * 0.15  # 答案长度权重
            )

            complexities.append(qa_complexity)

        return sum(complexities) / len(complexities)


class DataCurator:
    """数据管理器"""

    def __init__(self, config: ProcessorConfig):
        self.config = config

    def curate_dataset(self, examples: List[Dict[str, Any]]) -> List[
        Dict[str, Any]]:
        """数据集管理"""
        logger.info("开始数据集管理...")

        # 1. 质量过滤
        quality_filtered = self._quality_filter(examples)
        logger.info(f"质量过滤后剩余 {len(quality_filtered)} 个示例")

        # 2. 复杂度过滤
        complexity_filtered = self._complexity_filter(quality_filtered)
        logger.info(f"复杂度过滤后剩余 {len(complexity_filtered)} 个示例")

        # 3. 去重
        deduplicated = self._remove_duplicates(complexity_filtered)
        logger.info(f"去重后剩余 {len(deduplicated)} 个示例")

        # 4. 采样到目标大小
        final_dataset = self._sample_dataset(deduplicated)
        logger.info(f"最终数据集大小: {len(final_dataset)}")

        return final_dataset

    def _quality_filter(self, examples: List[Dict[str, Any]]) -> List[
        Dict[str, Any]]:
        """质量过滤"""
        filtered = []

        for example in examples:
            # 1. 检查问答对的质量
            qa_quality = self._check_qa_quality(example.get('qa_pairs', []))

            # 2. 检查文本质量
            text_quality = len(example.get('text', '').split()) >= 20  # 至少20个词

            if qa_quality and text_quality:
                filtered.append(example)

        return filtered

    def _check_qa_quality(self, qa_pairs: List[Dict[str, str]]) -> bool:
        """检查问答对的质量"""
        if not qa_pairs:
            return False

        for qa in qa_pairs:
            # 1. 长度检查
            if len(qa.get('question', '')) < 10 or len(
                    qa.get('answer', '')) < 5:
                return False

            # 2. 问答重复检查
            if qa.get('question', '') == qa.get('answer', ''):
                return False

        return True

    def _complexity_filter(self, examples: List[Dict[str, Any]]) -> List[
        Dict[str, Any]]:
        """复杂度过滤"""
        return [
            example for example in examples
            if example.get('metadata', {}).get('complexity',
                                               0) >= self.config.complexity_threshold
        ]

    def _remove_duplicates(self, examples: List[Dict[str, Any]]) -> List[
        Dict[str, Any]]:
        """去重"""
        seen = set()
        unique_examples = []

        for example in examples:
            # 使用文本和问答对的组合作为唯一标识
            text = example.get('text', '')
            qa_str = str(example.get('qa_pairs', []))

            identifier = hash(text + qa_str)

            if identifier not in seen:
                seen.add(identifier)
                unique_examples.append(example)

        return unique_examples

    def _sample_dataset(self, examples: List[Dict[str, Any]]) -> List[
        Dict[str, Any]]:
        """采样到目标数据集大小"""
        if len(examples) <= self.config.dataset_size:
            return examples

        return random.sample(examples, self.config.dataset_size)


def main():
    """示例用法"""
    # 创建处理器
    config = ProcessorConfig(
        seed=42,
        dataset_size=100,
        quality_threshold=0.7,
        complexity_threshold=0.5,
        use_ai_model=True,
        model_temperature=0.4,
        max_tokens=4096
    )

    processor = UserDataProcessor(config)

    # 示例：处理单个文本
    text = """
    Machine learning is a subset of artificial intelligence. It focuses on the development 
    of computer programs that can access data and use it to learn for themselves. 
    The process of learning begins with observations or data, such as examples, direct 
    experience, or instruction. The main aim is to allow the computers learn automatically 
    without human intervention or assistance and adjust actions accordingly.
    """

    result = processor.process_text(text, "example_source")
    logger.info(f"处理完成! 生成了 {len(result)} 个问答对")

    # 示例：批量处理多个文本
    texts = [
        "Text processing is the manipulation of text data. It involves various techniques like tokenization and normalization.",
        "Deep learning is a type of machine learning. It uses artificial neural networks with multiple layers.",
        "Natural language processing combines linguistics and computer science. It helps computers understand human language."
    ]

    results = processor.process_batch(texts)
    logger.info(f"批处理完成! 总共生成了 {len(results)} 个问答对")

    # 打印示例结果
    if results:
        print("\n示例问答对:")
        for i, result in enumerate(results[:2], 1):
            print(f"\n示例 {i}:")
            for qa in result['qa_pairs'][:2]:
                print(f"类型: {qa['type']}")
                print(f"问题: {qa['question']}")
                print(f"答案: {qa['answer']}\n")


if __name__ == "__main__":
    main()