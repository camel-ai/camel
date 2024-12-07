from apis.api import API
import json
import os
import datetime


class DeleteAgenda(API):
    description = "The API for deleting a schedule item includes parameters for token, content, time, and location."
    input_parameters = {
        'token': {'type': 'str', 'description': "User's token."},
        'content': {'type': 'str', 'description': 'The content of the agenda.'},
        'time': {'type': 'str', 'description': 'The time for agenda. Format: %Y-%m-%d %H:%M:%S'},
        'location': {'type': 'str', 'description': 'The location of the agenda.'},
    }
    output_parameters = {
        'status': {'type': 'str', 'description': 'success or failed'}
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
        if groundtruth['output'] == 'success' and response['output'] == 'success':
            if response['input']['time'] == groundtruth['input']['time']:
                return True
            else:
                return False

        if response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception']:
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
            status = self.delete_agenda(token, content, time, location)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': status,
                    'exception': None}

    def delete_agenda(self, token: str, content: str, time: str, location: str) -> str:
        # Check the format of the input parameters.
        if time:
            datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S')

        delete = False
        username = self.token_checker.check_token(token)
        for key in self.database:
            if self.database[key]['username'] == username:
                if self.database[key]['content'] == content or self.database[key][
                    'time'] == time:
                    del self.database[key]
                    delete = True
                    break
        if not delete:
            if content:
                raise Exception(f'You have no meeting about {content}')
            if time:
                raise Exception(f'You have no meeting at time : {time}')
        return "success"

