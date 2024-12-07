from apis.api import API
import json
import os
import datetime

class QueryAgenda(API):
    description = "The API for getting a schedule item includes parameters for token, content, time, and location."
    input_parameters = {
        'token': {'type': 'str', 'description': "User's token."},
        'content': {'type': 'str', 'description': 'The content of the agenda.'},
        'time': {'type': 'str', 'description': 'The time for agenda. Format: %Y-%m-%d %H:%M:%S'},
        'location': {'type': 'str', 'description': 'The location of the agenda.'},
    }
    output_parameters = {
        'info': {'type': 'json', 'description': 'agenda info including username and time'}
    }
    database_name = 'Agenda'

    def __init__(self, init_database=None, token_checker=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}
        self.token_checker = token_checker

    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response.

        Returns:
        - is_correct (bool): whether the response is correct.
        """
        response_content, groundtruth_content = response['input']['content'].split(" "), groundtruth['input'][
            'content'].split(" ")
        content_satisfied = False
        if len(set(response_content).intersection(set(groundtruth_content))) / len(set(response_content).union(
                set(groundtruth_content))) > 0.5:
            content_satisfied = True

        if content_satisfied and response['input']['time'] == groundtruth['input']['time'] \
                and response['input']['location'] == groundtruth['input']['location'] and response['output'] == \
                groundtruth['output'] and response['exception'] == groundtruth['exception']:
            return True
        else:
            return False

    def call(self, token: str, content: str, time: str, location: str) -> dict:
        input_parameters = {
            'token': token,
            'content': content,
            'time': time,
            'location': location
        }
        try:
            status = self.get_agenda(token, content, time, location)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': status,
                    'exception': None}

    def get_agenda(self, token: str, content: str, time: str, location: str) -> str:
        # Check the format of the input parameters.
        if time:
            datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S')

        username = self.token_checker.check_token(token)
        for key in self.database:
            if self.database[key]['username'] == username:
                if self.database[key]['content'] == content or self.database[key][
                    'time'] == time:
                    return self.database[key]
        if content:
            raise Exception(f'You have no agenda about {content}')
        if time:
            raise Exception(f'You have no agenda at time : {time}')
        raise Exception(f'Error')

