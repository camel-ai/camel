from apis.api import API
import json
import os
import datetime


class DeleteReminder(API):
    
    description = "The API for deleting a reminder item includes content and time."
    input_parameters = {
        'token': {'type': 'str', 'description': "User's token."},
        'content': {'type': 'str', 'description': 'The content of the conference.'},
        'time': {'type': 'str', 'description': 'The time for conference. Format: %Y-%m-%d %H:%M:%S'}
    }
    output_parameters = {
        'status': {'type': 'str', 'description': 'success or failed'}
    }

    database_name = 'Reminder'

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

    def call(self, token: str, content: str, time: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - token (str) : user's token
        - content (str): the content of the remind.
        - time (datetime): the time of remind.

        Returns:
        - response (str): the statu from the API call.
        """
        input_parameters = {
            'token': token,
            'content': content,
            'time': time
        }
        try:
            status = self.delete_remind(token, content, time)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': status,
                    'exception': None}

    def delete_remind(self, token: str, content: str, time: str) -> str:
        """
        Delete a remind.

        Parameters:
        - token (str) : user's token
        - content (str): the content of the remind.
        - time (datetime): the time of remind.
        Returns:
        - response (str): the statu from the API call.
        """

        # Check the format of the input parameters.
        datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S')

        if content.strip() == "":
            raise Exception('Content should not be null')

        delete = False
        username = self.token_checker.check_token(token)
        for key in self.database:
            if self.database[key]['username'] == username:
                if self.database[key]['content'] == content or self.database[key]['time'] == time:
                    del self.database[key]
                    delete = True
                    break
        if not delete:
            raise Exception(f'You have no reminder about {content} or at time : {time}')
        return "success"

