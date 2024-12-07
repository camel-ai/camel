from apis.api import API
import json
import os
import datetime


class OpenBankAccount(API):
    description = "This is an API for opening a bank account for a user, given the account, password and name."
    input_parameters = {
        'account': {'type': 'str', 'description': 'The account for the user.'},
        'password': {'type': 'str', 'description': 'The password.'},
        'name': {'type': 'str', 'description': 'account holder name.'}
    }
    output_parameters = {
        'status': {'type': 'str', 'description': 'success or failed'}
    }

    def __init__(self) -> None:
        # database contains id, content, time
        self.database = {0:{"account":"test", "password":"test","name":"yifei"}}

    def dump_database(self, database_dir):
        json.dump(self.database, open(os.path.join(database_dir, 'open_banck_account.json'), 'w'), ensure_ascii=False)

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

    def call(self, account: str, password: str, name: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - account (str): The account for the user.
        - password (str): The password.
        - name (str): account holder name.

        Returns:
        - response (str): the statu from the API call.
        """
        input_parameters = {
            'account': account,
            'password': password,
            'name': name
        }
        try:
            status = self.open_bank_account(account, password, name)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': status,
                    'exception': None}

    def open_bank_account(self, account: str, password: str, name: str) -> str:
        """
        The function to open bank account.

        Parameters:
        - account (str): The account for the user.
        - password (str): The password.
        - name (str): account holder name.
        Returns:
        - response (str): the statu from the API call.
        """

        # Check the format of the input parameters.
        for key in self.database:
            if self.database[key]['account'] == account:
                return "failed"

        # write to database
        id_now = len(self.database) + 1
        self.database[id_now] = {
            'account': account,
            'password': password,
            'name': name
        }
        return "success"

