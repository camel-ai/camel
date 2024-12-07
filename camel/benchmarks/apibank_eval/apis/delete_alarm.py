from apis.api import API
import json
import os
import datetime


class DeleteAlarm(API):
    description = "The API for removing an alarm includes a parameter for the time."
    input_parameters = {
        'token': {'type': 'str', 'description': "User's token."},
        'time': {'type': 'str', 'description': 'The time for alarm. Format: %Y-%m-%d %H:%M:%S'}
    }
    output_parameters = {
        'status': {'type': 'str', 'description': 'success or failed'}
    }

    database_name = 'Alarm'

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
        if response['input'] == groundtruth['input'] and response['output'] == \
                groundtruth['output'] and response['exception'] == groundtruth['exception']:
            return True
        else:
            return False

    def call(self, token:str, time: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - time (datetime): the time of alarm clock.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'token': token,
            'time': time,
        }
        try:
            status = self.delete_alarm_clock(token, time)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': status,
                    'exception': None}

    def delete_alarm_clock(self, token: str, time: str) -> str:
        """
        Add alarm clock.

        Parameters:
        - time (datetime): the time of alarm clock.
        Returns:
        - order_id (str): the ID of the order.
        """

        # Check the format of the input parameters.
        datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S')

        delete = False
        username = self.token_checker.check_token(token)
        for key in self.database:
            if self.database[key]['username'] == username:
                if self.database[key]['time'] == time:
                    del self.database[key]
                    delete = True
                    break
        if not delete:
            if time:
                raise Exception(f'You have no alarm clock at time : {time}')
        return "success"
