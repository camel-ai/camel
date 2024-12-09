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
import logging
import os
import random
import re
import numpy as np
from pathlib import Path
from rouge import Rouge
from typing import Any, Dict, List, Literal, Optional

from tqdm import tqdm
from .apibank_eval.api_call_extraction import parse_api_call
from .apibank_eval.tool_manager import ToolManager
from camel.agents import ChatAgent
from camel.benchmarks import BaseBenchmark
from camel.messages.base import BaseMessage
from camel.models.model_factory import ModelFactory

logger = logging.getLogger(__name__)

def agent_call(messages: List[Dict], agent: ChatAgent):
    r"""Add messages to agent memory and get response."""
    for i, msg in enumerate(messages):
        if msg['role'] == 'user':
            message = BaseMessage.make_user_message(
                role_name="CAMEL User",
                content=msg['content']
            )
        elif msg['role'] == 'assistant':
            message = BaseMessage.make_assistant_message(
                role_name="CAMEL Assistant",
                content=msg['content']
            )
        elif msg['role'] == 'system':
            message = BaseMessage.make_assistant_message(
                role_name="System",
                content=msg['content']
            )
        else:
            raise ValueError(f"Unrecognized role: {msg['role']}")
        
        if i == len(messages) - 1:
            break
        agent.record_message(message)

    response = agent.step(message)
    model_output = response.msgs[0].content
    logger.info("\nanswer:", model_output)
    agent.reset()
    return model_output

def calculate_rouge_l_score(reference, hypothesis):
    r"""Calculate rouge l score between hypothesis and reference."""
    rouge = Rouge()
    scores = rouge.get_scores(hypothesis, reference)
    rouge_l_score = scores[0]['rouge-l']['f']
    return rouge_l_score

def get_api_call(model_output):
    r"""Parse api call from model output."""
    api_call_pattern = r"\[(\w+)\((.*)\)\]"
    api_call_pattern = re.compile(api_call_pattern)
    match = api_call_pattern.search(model_output)
    if match:
        return match.group(0)
    else:
        return None

class APIBankSample:
    r"""APIBank sample used to load the datasets."""
    def __init__(self, chat_history, apis, ground_truth):
        self.chat_history = chat_history
        self.apis = apis
        self.ground_truth = ground_truth

    def __repr__(self):
        return 'Sample(chat_history={}, apis={}, ground_truth={})'.format(self.chat_history, self.apis, self.ground_truth)
        # return 'Chat history: {}, apis: {}, ground truth: {}'.format(self.chat_history, self.apis, self.ground_truth)

    @classmethod
    def from_chat_history(cls, chat_history):
        apis = set()
        api_positions = []
        for i, item in enumerate(chat_history):
            if item['role'] == 'API':
                apis.add(item['api_name']) 
                api_positions.append(i)

        samples = []
        for i in api_positions:
            sample = cls(chat_history[:i], apis, chat_history[i])
            samples.append(sample)
            sample = cls(chat_history[:i + 1], apis, chat_history[i + 1])
            samples.append(sample)

        return samples

class Evaluator:
    r"""Evaluator for APIBank benchmark."""
    def __init__(self, samples: List[APIBankSample]):
        self.dataset = samples
        self.sample_ids = list(range(len(self.dataset)))

    def get_all_sample_ids(self):
        return self.sample_ids
    
    def get_api_description(self, api_name):
        tool_manager = ToolManager()
        return tool_manager.get_api_description(api_name)
     
    def get_model_input(self, sample_id: int):
        sample = self.dataset[sample_id]
        apis = sample.apis
        chat_history = sample.chat_history
        tool_manager = ToolManager()
        api_descriptions = []
        for api_name in apis:
            api_descriptions.append(tool_manager.get_api_description(api_name))
        api_descriptions = '\n'.join(api_descriptions)
        return api_descriptions, chat_history

    def evaluate(self, sample_id, model_output):
        # model_output [ApiName(param1=value1, param2=value2), ...)]
        tool_manager = ToolManager()

        sample = self.dataset[sample_id]
        ground_truth = sample.ground_truth
        if ground_truth['role'] == 'API':
            api_name, param_dict = parse_api_call(model_output)
            if api_name != ground_truth['api_name']:
                return False, 'API Name Mismatch: {} vs {}'.format(api_name, ground_truth['api_name'])
            try:
                result = tool_manager.api_call(api_name, **param_dict)
            except Exception as e:
                return False, str(e)
            api = tool_manager.init_tool(api_name)
            try:
                correct = api.check_api_call_correctness(result, ground_truth['result'])
            except KeyError:
                correct = False
                result = 'KeyError' + str(result)
            return correct, result
        elif ground_truth['role'] == 'AI':
            score = calculate_rouge_l_score(ground_truth['text'], model_output)
            return round(score, 4)
        
api_call_prompt = '''
Based on the given API description and the existing conversation history 1..t, please generate the API request that the AI should call in step t+1 and output it in the format of [ApiName(key1='value1', key2='value2', ...)], replace the ApiName with the actual API name, and replace the key and value with the actual parameters. 
Your output should start with a square bracket "[" and end with a square bracket "]". Do not output any other explanation or prompt or the result of the API call in your output. 
This year is 2023.
Input: 
User: [User's utterence]
AI: [AI's utterence]

Expected output:
[ApiName(key1='value1', key2='value2', ...)]

API descriptions:
'''

response_prompt = '''
Based on the given API description and the existing conversation history 1..t, please generate the next dialog that the AI should response after the API call t.
This year is 2023.
Input: 
User: [User's utterence]
AI: [AI's utterence]
[ApiName(key1='value1', key2='value2', …)]

Expected output:
AI: [AI's utterence]

API descriptions:
'''

class APIBankBenchmark(BaseBenchmark):
    r"""
    API-Bank Benchmark adapted from `API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs`
    <https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/api-bank>.

    Args:
        data_dir (str): The directory to save the data.
        save_to (str): The file to save the results.
        processes (int, optional): The number of processes to use.
            (default: :obj:`1`)
    """

    def __init__(
        self,
        save_to: str,
        processes: int = 1,
    ):
        super().__init__("apibank", 'camel/benchmarks/apibank_eval', save_to, processes)
        self._data: Dict[str, List[APIBankSample]]

    def download(self):
        r"""APIBank benchmark dataset is not available for download from huggingface."""
        logger.info("Dataset is not available for download.")

    def load(self, level):
        r"""Load the APIBank Benchmark dataset.

        Args:
            level: Level to run benchmark on.
        """
        current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        if level == "level-1":
            file_path = current_dir / "apibank_eval/lv1-lv2-samples/level-1-given-desc"
        elif level == 'level-2':
            file_path = current_dir / "apibank_eval/lv1-lv2-samples/level-2-toolsearcher"
        jsonl_files = [f for f in os.listdir(file_path) if f.endswith('.jsonl')]
        for file in tqdm(jsonl_files, desc="Processing files"):
            history  = []
            with open(file_path / file, 'r') as f:
                for line in f:
                    history.append(json.loads(line))
                samples = APIBankSample.from_chat_history(history)
                self._data[file.rsplit('.', 1)[0]] = samples

    def run(  # type: ignore[override]
        self,
        agent: ChatAgent,
        level: Literal[
            "level-1",
            "level-2",
            "level-3"
        ],
        api_test_enabled = True,
        randomize: bool = False,
        subset: Optional[int] = None,
    ) -> Dict[str, Any]:
        r"""Run the benchmark.

        Args:
            agent (ChatAgent): The agent to run the benchmark.
            level (Literal['level-1', 'level-2', 'level-3']): The level to run the benchmark on.
            randomize (bool, optional): Whether to randomize the data.
            api_test_enabled (bool): Whether to test API calling (`True`) or response (`False`)
                (default: :obj:`False`)
            subset (Optional[int], optional): The subset of data to run.
                (default: :obj:`None`)

        Returns:
            Dict[str, Any]: The results of the benchmark.
        """
        
        total_api_calls = 0
        correct_api_calls = 0
        rougel_scores = []
        
        logger.info(f"Running APIBench benchmark on {level}.")
        self.load(level)
        datas = self._data
        if randomize:
            random.shuffle(datas)
        if subset:
            datas = datas[:subset]
        logger.info(f"Number of tasks: {len(datas)}")
        self._results = []

        if level == 'level-1':
            tool_search_enabled = False
        else:
            tool_search_enabled = True

        dialog_test_enabled = not api_test_enabled

        with open(self.save_to, "w") as f:
            for test in tqdm(datas, desc="Running"):
                samples = self._data[test]
                evaluator = Evaluator(samples)

                for sample_id in evaluator.get_all_sample_ids():
                    sample = evaluator.dataset[sample_id]

                    if sample.ground_truth['role'] == 'API' and api_test_enabled:
                        if tool_search_enabled:
                            _, chat_history = evaluator.get_model_input(sample_id)
                            api_descriptions = evaluator.get_api_description('ToolSearcher')
                        else:
                            api_descriptions, chat_history = evaluator.get_model_input(sample_id)
                        prompt = api_call_prompt + api_descriptions
                        messages = [
                            {'role': 'system', 'content': prompt},
                        ]
                        for item in chat_history:
                            if item['role'] == 'User':
                                chat_role = 'user'
                                chat_content = item['text']
                            elif item['role'] == 'AI':
                                chat_role = 'assistant'
                                chat_content = item['text']
                            elif item['role'] == 'API':
                                chat_role = 'system'
                                chat_content = '[{}({})] Response: {}'.format(item['api_name'], ', '.join(['{}=\'{}\''.format(k, v) for k, v in item['param_dict'].items()]), str(item['result']['output']))
                            else:
                                raise ValueError('Invalid chat role: {}'.format(item['role']))
                            messages.append({'role': chat_role, 'content': chat_content})
                        
                        model_output = agent_call(messages, agent)

                        api_call = get_api_call(model_output)

                        if api_call:
                            try:
                                correct, model_output_result = evaluator.evaluate(sample_id, api_call)
                            except AssertionError as e:
                                if not 'The API name is not correct.' in str(e):
                                    raise e
                                logging.info('AssertionError: {}'.format(e))
                                correct = False
                        else:
                            model_output_result = 'No API call found'
                            correct = False
                        if correct:
                            correct_api_calls += 1
                            logging.info('Correct API call: {} Ground truth: {}'.format(api_call, sample.ground_truth))
                        else:                    
                            logging.info('Incorrect model output: {} Result: {} Ground truth: {} File: {} Sample ID: {} Messages: {}'.format(model_output.replace('\n', ' '), model_output_result, sample.ground_truth, test, sample_id, messages[1:]))
                        total_api_calls += 1
                        self._results.append(
                            {
                                'Role': 'API',
                                'Model_output': model_output,
                                'Model_output_result': model_output_result,
                                'Ground_truth': sample.ground_truth,
                                'Test': test,
                                'Correct': correct,
                            }
                        )
                        f.write(json.dumps(self._results[-1], indent=2) + "\n")

                    elif sample.ground_truth['role'] == 'AI' and dialog_test_enabled:
                        api_descriptions, chat_history = evaluator.get_model_input(sample_id)
                        prompt = response_prompt + api_descriptions
                        messages = [
                            {'role': 'system', 'content': prompt},
                        ]
                        for item in chat_history:
                            if item['role'] == 'User':
                                chat_role = 'user'
                                chat_content = item['text']
                            elif item['role'] == 'AI':
                                chat_role = 'assistant'
                                chat_content = item['text']
                            elif item['role'] == 'API':
                                chat_role = 'system'
                                chat_content = '[{}({})] Response: {}'.format(item['api_name'], ', '.join(['{}=\'{}\''.format(k, v) for k, v in item['param_dict'].items()]), str(item['result']['output']))
                            else:
                                raise ValueError('Invalid chat role: {}'.format(item['role']))
                            messages.append({'role': chat_role, 'content': chat_content})

                        model_output = agent_call(messages, agent)

                        if model_output:
                            score = evaluator.evaluate(sample_id, model_output)
                        else:
                            score = 0    
                        rougel_scores.append(score)
                        if score < 0.2:
                            logging.info('Low score: {} Score: {} Ground truth: {} Test: {} Sample ID: {} Messages: {}'.format(model_output.replace('\n', ' '), score, sample.ground_truth, test, sample_id, messages[1:]))
                            
                        self._results.append(
                            {   
                                'Role': 'AI',
                                'Model_output': model_output,
                                'Score': score,
                                'Ground_truth': sample.ground_truth,
                                'Test': test,
                            }
                        )
                        f.write(json.dumps(self._results[-1], indent=2) + "\n")
                    
                    f.flush()

        if api_test_enabled:
            return {
                'total': total_api_calls,
                'correct': correct_api_calls,
                "accuracy": correct_api_calls / total_api_calls,
            }
        elif dialog_test_enabled:
            return {
                'Dialog_score': np.mean()
            }
            