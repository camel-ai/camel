import json
from tool_manager import ToolManager
import re
from rouge import Rouge
import os
from utils import ChatGPTWrapper, DavinciWrapper
import logging
from tqdm import tqdm
from api_call_extraction import parse_api_call
from datetime import datetime
import numpy as np

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

    def __str__(self) -> str:
        return self.__repr__()

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
            try:
                api_name, param_dict = parse_api_call(model_output)
            except Exception as e:
                raise Exception('Parse API Call Error: {}'.format(model_output))
            if api_name != ground_truth['api_name']:
                return False, 'API Name Mismatch: {} vs {}'.format(api_name, ground_truth['api_name'])
            # try:
            result = tool_manager.api_call(api_name, **param_dict)
            # except Exception as e:
            #     return False, str(e)
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

if __name__ == '__main__':
    data_dir = 'lv1-lv2-samples/level-1-given-desc'
    evaluation_path = 'path-to-json'
    api_test_enabled = True
    dialog_test_enabled = not api_test_enabled

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename=evaluation_path.replace('.json', '.log'), filemode='w')

    if os.path.basename(data_dir).endswith('given-desc'):
        tool_search_enabled = False
    else:
        tool_search_enabled = True
   
    with open(evaluation_path, 'r') as f:
        predictions = [json.loads(line) for line in f]
    pred_map = {}
    for pred in predictions:
        if pred['file'] not in pred_map:
            pred_map[pred['file']] = {}
        pred_map[pred['file']][pred['id']] = pred

    total_api_calls = 0
    correct_api_calls = 0
    total_after_api_response = 0
    total_score_after_api_response = 0

    rougel_scores = []

    error_statistic = {
        'NO_API_CALL': {
            'count': 0,
            'samples': []
        },
        'API_NAME_MISMATCH': {
            'count': 0,
            'samples': []
        },
        'HAS_EXCEPTION': {
            'count': 0,
            'samples': []
        },
        'INPUT_MISMATCH': {
            'count': 0,
            'samples': []
        },
        'OUTPUT_MISMATCH': {
            'count': 0,
            'samples': []
        },
        'INVALID_INPUT_PARAMETER': {
            'count': 0,
            'samples': []
        },
        'KEY_ERROR': {
            'count': 0,
            'samples': []
        },
        'FAILED_PARSE_API_CALL': {
            'count': 0,
            'samples': []
        },
        'MISS_INPUT_ARGUMENT': {
            'count': 0,
            'samples': []
        },
    }

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
                total_api_calls += 1

                # assert file in pred_map
                # assert sample_id in pred_map[file]
                if sample_id not in pred_map[file]:
                    continue
                model_output = pred_map[file][sample_id]['pred']

                api_call = get_api_call(model_output)
                if api_call:
                    try:
                        correct, model_output_result = evaluator.evaluate(sample_id, api_call)
                    except AssertionError as e:
                        if 'The API name is not correct.' in str(e):
                            error_statistic['API_NAME_MISMATCH']['count'] += 1
                            error_statistic['API_NAME_MISMATCH']['samples'].append(
                                {'file': file, 'sample_id': sample_id, 'model_output': model_output, 'sample': sample, 'pred': pred_map[file][sample_id]}
                            )
                            continue
                        elif 'invalid parameter name' in str(e):
                            error_statistic['INVALID_INPUT_PARAMETER']['count'] += 1
                            error_statistic['INVALID_INPUT_PARAMETER']['samples'].append(
                                {'file': file, 'sample_id': sample_id, 'model_output': model_output, 'sample': sample, 'pred': pred_map[file][sample_id]}
                            )
                            continue
                        raise e
                    except Exception as e:
                        if 'Parse API Call Error' in str(e):
                            error_statistic['FAILED_PARSE_API_CALL']['count'] += 1
                            error_statistic['FAILED_PARSE_API_CALL']['samples'].append(
                                {'file': file, 'sample_id': sample_id, 'model_output': model_output, 'sample': sample, 'pred': pred_map[file][sample_id]}
                            )
                            continue
                        if 'missing' in str(e) and 'required positional argument' in str(e):
                            error_statistic['MISS_INPUT_ARGUMENT']['count'] += 1
                            error_statistic['MISS_INPUT_ARGUMENT']['samples'].append(
                                {'file': file, 'sample_id': sample_id, 'model_output': model_output, 'sample': sample, 'pred': pred_map[file][sample_id]}
                            )
                            continue
                        raise e

                else:
                    model_output_result = 'No API call found'
                    error_statistic['NO_API_CALL']['count'] += 1
                    error_statistic['NO_API_CALL']['samples'].append(
                        {'file': file, 'sample_id': sample_id, 'model_output': model_output, 'sample': sample, 'pred': pred_map[file][sample_id]}
                    )
                    continue
                if isinstance(model_output_result, str) and model_output_result.startswith('API Name Mismatch'):
                    error_statistic['API_NAME_MISMATCH']['count'] += 1
                    error_statistic['API_NAME_MISMATCH']['samples'].append(
                        {'file': file, 'sample_id': sample_id, 'model_output': model_output, 'sample': sample, 'pred': pred_map[file][sample_id]}
                    )
                    continue
                if isinstance(model_output_result, str) and model_output_result.startswith('KeyError'):
                    error_statistic['KEY_ERROR']['count'] += 1
                    error_statistic['KEY_ERROR']['samples'].append(
                        {'file': file, 'sample_id': sample_id, 'model_output': model_output, 'sample': sample, 'pred': pred_map[file][sample_id]}
                    )
                    continue

                if correct:
                    correct_api_calls += 1
                    logging.info('Correct API call: {} Ground truth: {}'.format(api_call, sample.ground_truth))
                else:                    
                    logging.info('Incorrect model output: {} Result: {} Ground truth: {} File: {} Sample ID: {} '.format(model_output.replace('\n', ' '), model_output_result, sample.ground_truth, file, sample_id))
                    assert isinstance(model_output_result, dict)
                    if model_output_result['exception']:
                        error_statistic['HAS_EXCEPTION']['count'] += 1
                        error_statistic['HAS_EXCEPTION']['samples'].append(
                            {'file': file, 'sample_id': sample_id, 'model_output': model_output, 'model_output_result': model_output_result, 'sample': sample, 'pred': pred_map[file][sample_id]}
                        )
                        continue
                    if model_output_result['output'] != sample.ground_truth['result']['output']:
                        error_statistic['OUTPUT_MISMATCH']['count'] += 1
                        error_statistic['OUTPUT_MISMATCH']['samples'].append(
                            {'file': file, 'sample_id': sample_id, 'model_output': model_output, 'model_output_result': model_output_result, 'sample': sample, 'pred': pred_map[file][sample_id]}
                        )
                        continue
                    if model_output_result['input'] != sample.ground_truth['result']['input']:
                        error_statistic['INPUT_MISMATCH']['count'] += 1
                        error_statistic['INPUT_MISMATCH']['samples'].append(
                            {'file': file, 'sample_id': sample_id, 'model_output': model_output, 'model_output_result': model_output_result, 'sample': sample, 'pred': pred_map[file][sample_id]}
                        )
                        continue                    
            elif sample.ground_truth['role'] == 'AI' and dialog_test_enabled:
                assert file in pred_map
                assert sample_id in pred_map[file]
                model_output = pred_map[file][sample_id]['pred']

                if model_output:
                    score = evaluator.evaluate(sample_id, model_output)
                else:
                    score = 0    
                rougel_scores.append(score)
                if score < 0.2:
                    logging.info('Low score: {} Score: {} Ground truth: {} File: {} Sample ID: {}'.format(model_output.replace('\n', ' '), score, sample.ground_truth, file, sample_id))

    def print_error_samples(sample):
        print('Instruction: \n{}\n'.format(sample['pred']['instruction']))
        print('Input: \n{}\n'.format(sample['pred']['input']))
        print('Output: \n{}\n'.format(sample['model_output']))
        print('Ground truth: \n{}\n'.format(sample['pred']['expected_output']))


    print('Error statistic: {}'.format(error_statistic))
    for key in error_statistic:
        print(key, error_statistic[key]['count'])

    if dialog_test_enabled:
        print('Dialog score: {:.4f}'.format(np.mean(rougel_scores)))

    if api_test_enabled:
        print('Total API calls: {}'.format(total_api_calls))
        print('Correct API calls: {}'.format(correct_api_calls))
        print('Accuracy: {:.4f}'.format(correct_api_calls / total_api_calls))
        logging.info('Total API calls: {}'.format(total_api_calls))
        logging.info('Correct API calls: {}'.format(correct_api_calls))
        logging.info('Accuracy: {:.4f}'.format(correct_api_calls / total_api_calls))
