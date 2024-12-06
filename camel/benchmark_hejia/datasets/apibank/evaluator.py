import json
from .tool_manager import ToolManager
import re
from rouge import Rouge
import os
import logging
from tqdm import tqdm
from .api_call_extraction import parse_api_call
from datetime import datetime
import numpy as np
from camel.messages import BaseMessage

def agent_call(messages, agent):
  # 逐条记录历史消息到 agent 的记忆
    for i, msg in enumerate(messages):
        # 根据角色选择不同的消息生成方法
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
        
        # 记录消息到 agent 的记忆
        if i == len(messages) - 1:
            break
        agent.record_message(message)

    response = agent.step(message)
    model_output = response.msgs[0].content
    print("\nanswer:", model_output)
    agent.reset()
    return model_output

def calculate_rouge_l_score(reference, hypothesis):
    rouge = Rouge()
    scores = rouge.get_scores(hypothesis, reference)
    rouge_l_score = scores[0]['rouge-l']['f']
    return rouge_l_score

class Sample:
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

    def __init__(self, samples):
        self.dataset = samples
        self.sample_ids = list(range(len(self.dataset)))

    def get_all_sample_ids(self):
        return self.sample_ids
    
    def get_api_description(self, api_name):
        tool_manager = ToolManager()
        return tool_manager.get_api_description(api_name)

    
    def get_model_input(self, sample_id):
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
        

def get_api_call(model_output):
    api_call_pattern = r"\[(\w+)\((.*)\)\]"
    api_call_pattern = re.compile(api_call_pattern)
    match = api_call_pattern.search(model_output)
    if match:
        return match.group(0)
    else:
        return None


def eval_apibank(data_level, api_test_enabled = False, agent = None):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if data_level == 'level1':
        print('level1')
        data_dir = os.path.join(current_dir, 'lv1-lv2-samples/level-1-given-desc')
    elif data_level == 'level2':
        print('level2')
        data_dir = os.path.join(current_dir, 'lv1-lv2-samples/level-2-toolsearcher')
    else:
        raise ValueError('Invalid data level: {}'.format(data_level))
    
    print('API test enabled: {}'.format(api_test_enabled))
    dialog_test_enabled = not api_test_enabled

    if os.path.basename(data_dir).endswith('given-desc'):
        tool_search_enabled = False
    else:
        tool_search_enabled = True

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

    total_api_calls = 0
    correct_api_calls = 0
    total_after_api_response = 0
    total_score_after_api_response = 0

    rougel_scores = []

    jsonl_files = [f for f in os.listdir(data_dir) if f.endswith('.jsonl')]

    for file in tqdm(jsonl_files, desc='Processing files', ncols=100):
        history = []
        with open(os.path.join(data_dir, file), 'r') as f:
            for line in f:
                history.append(json.loads(line))
        samples = Sample.from_chat_history(history)
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
                    logging.info('Incorrect model output: {} Result: {} Ground truth: {} File: {} Sample ID: {} Messages: {}'.format(model_output.replace('\n', ' '), model_output_result, sample.ground_truth, file, sample_id, messages[1:]))
                total_api_calls += 1
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
                    logging.info('Low score: {} Score: {} Ground truth: {} File: {} Sample ID: {} Messages: {}'.format(model_output.replace('\n', ' '), score, sample.ground_truth, file, sample_id, messages[1:]))


    if dialog_test_enabled:
        print('Dialog score: {:.4f}'.format(np.mean(rougel_scores)))

    if api_test_enabled:
        print('Total API calls: {}'.format(total_api_calls))
        print('Correct API calls: {}'.format(correct_api_calls))
        print('Accuracy: {:.4f}'.format(correct_api_calls / total_api_calls))
        logging.info('Total API calls: {}'.format(total_api_calls))
        logging.info('Correct API calls: {}'.format(correct_api_calls))
        logging.info('Accuracy: {:.4f}'.format(correct_api_calls / total_api_calls))

