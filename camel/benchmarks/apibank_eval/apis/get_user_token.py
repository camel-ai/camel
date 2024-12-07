from apis.api import API
import json
import os
class GetUserToken(API):

    description = 'Get the user token by username and password.'
    input_parameters = {
        'username': {'type': 'str', 'description': 'The username of the user.'},
        'password': {'type': 'str', 'description': 'The password of the user.'},
    }
    output_parameters = {
        'token': {'type': 'str', 'description': 'The token of the user.'},
    }
    database_name = 'Account'
    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def get_user_token(self, username: str, password: str) -> str:
        """
        Gets the user token.

        Parameters:
        - username (str): the username of the user.
        - password (str): the password of the user.

        Returns:
        - token (str): the token of the user.
        """
        if username not in self.database:
            raise Exception('The username does not exist.')
        if self.database[username]['password'] != password:
            raise Exception('The password is incorrect.')
        return self.database[username]['token']
    
    def call(self, username: str, password: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - username (str): the username of the user.
        - password (str): the password of the user.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'username': username,
            'password': password,
        }
        try:
            token = self.get_user_token(username, password)
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
                'token': token,
            },
            'exception': None,
        }
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - target (dict): the target response.

        Returns:
        - is_correct (bool): whether the response is correct.
        """
        if response['input'] == groundtruth['input'] and response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception']:
            return True
        else:
            return False
        
    def dump_database(self, database_dir):
        json.dump(self.database, open(os.path.join(database_dir, 'Account.json'), 'w'), ensure_ascii=False)


