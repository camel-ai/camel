from .api import API
import datetime

class GetToday(API):
    description = 'This API gets the current date.'
    input_parameters = {}
    output_parameters = {
        'date': {'type': 'str', 'description': 'The current date. Format: %Y-%m-%d'},
    }
    def call(self, **kwargs) -> dict:
        # today is 2023-03-31
        return {'api_name': self.__class__.__name__, 'input': None, 'output': "2023-03-31", 'exception': None}
        # return {'api_name': self.__class__.__name__, 'input': None, 'output': datetime.datetime.now().strftime('%Y-%m-%d'), 'exception': None}
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        return response['output'] != None and response['exception'] == None and response['input'] == None