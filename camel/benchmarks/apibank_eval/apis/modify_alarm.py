from apis.api import API
import json
import os
import datetime


class ModifyAlarm(API):
    description = "The API for modifying an alarm includes a parameter for the from_time to to_time."
    input_parameters = {
        'token': {'type': 'str', 'description': "User's token."},
        'from_time': {'type': 'str', 'description': 'The time for alarm which changed from. Format: %Y-%m-%d %H:%M:%S'},
        'to_time': {'type': 'str', 'description': 'The time for alarm which changed to. Format: %Y-%m-%d %H:%M:%S'},
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

    def call(self, token:str, from_time: str, to_time: str) -> dict:

        input_parameters = {
            'token': token,
            'from_time': from_time,
            'to_time': to_time,
        }
        try:
            status = self.modify_alarm_clock(token, from_time,to_time)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': status,
                    'exception': None}

    def modify_alarm_clock(self, token: str, from_time:str, to_time: str) -> str:
        """
        Add alarm clock.

        Parameters:
        - time (datetime): the time of alarm clock.
        Returns:
        - order_id (str): the ID of the order.
        """

        # Check the format of the input parameters.
        datetime.datetime.strptime(from_time, '%Y-%m-%d %H:%M:%S')
        datetime.datetime.strptime(to_time, '%Y-%m-%d %H:%M:%S')

        username = self.token_checker.check_token(token)
        for key in self.database:
            if self.database[key]['username'] == username:
                if self.database[key]['time'] == from_time:
                    self.database[key] = {
                        'username': username,
                        'time': to_time,
                    }
                    return 'success'
        raise Exception(f'You have no agenda at time : {from_time}')
