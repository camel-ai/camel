from apis.api import API
import json

class ModifyPassword(API):

    description = 'The API for modifying the password of the account.'
    input_parameters = {
        'token': {'type': 'str', 'description': 'The token of the user.'},
        'old_password': {'type': 'str', 'description': 'The old password of the user.'},
        'new_password': {'type': 'str', 'description': 'The new password of the user.'},
    }
    output_parameters = {
        'status': {'type': 'str', 'description': 'success or failed'}
    }
    database_name = 'Account'
    def __init__(self, init_database=None, token_checker=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}
        self.token_checker = token_checker

    def modify_password(self, token: str, old_password: str, new_password: str) -> str:
        """
        Modifies the password of the account.

        Parameters:
        - token (str): the token of the user.
        - old_password (str): the old password of the user.
        - new_password (str): the new password of the user.

        Returns:
        - status (str): success or failed
        """
        username = self.token_checker.check_token(token)
        if self.database[username]['password'] != old_password:
            raise Exception('The old password is incorrect.')
        self.database[username]['password'] = new_password
        return 'success'
    
    def call(self, token: str, old_password: str, new_password: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - token (str): the token of the user.
        - old_password (str): the old password of the user.
        - new_password (str): the new password of the user.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'token': token,
            'old_password': old_password,
            'new_password': new_password,
        }
        try:
            status = self.modify_password(token, old_password, new_password)
        except Exception as e:
            exception = str(e)
            return {
                'api_name': self.__class__.__name__,
                'input': input_parameters,
                'output': None,
                'exception': exception,
            }
        return {
            'api_name': self.__class__.__name__,
            'input': input_parameters,
            'output': {
                'status': status,
            },
            'exception': None,
        }
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks if the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth of the API call.

        Returns:
        - is_correct (bool): True if the API call is correct, False otherwise.
        """
        if response['input'] != groundtruth['input']:
            return False
        if response['exception'] != groundtruth['exception']:
            return False
        if response['output'] != groundtruth['output']:
            return False
        return True
    
