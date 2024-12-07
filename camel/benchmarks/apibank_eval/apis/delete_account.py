from apis.api import API
import json

class DeleteAccount(API):

    description = 'Delete an account.'
    input_parameters = {
        'token': {'type': 'str', 'description': 'The token of the user.'},
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

    def delete_account(self, token: str) -> str:
        """
        Deletes the account.

        Parameters:
        - token (str): the token of the user.

        Returns:
        - status (str): success or failed
        """
        if self.token_checker != None:
            self.token_checker.check_token(token)
        else:
            raise Exception('Lack of token checker.')

        username = self.token_checker.check_token(token)
        if username in self.database:
            del self.database[username]
            return 'success'
        raise Exception('No such user.')
    
    def call(self, token: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - token (str): the token of the user.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'token': token,
        }
        try:
            status = self.delete_account(token)
        except Exception as e:
            exception = str(e)
            return {
                'input': input_parameters,
                'output': None,
                'exception': exception,
            }
        return {
            'input': input_parameters,
            'output': {
                'status': status,
            },
            'exception': None,
        }
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks the correctness of the API call.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth of the API call.

        Returns:
        - correctness (bool): True if the API call is correct, False otherwise.
        """
        if response['input'] == groundtruth['input'] and response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception']:
            return True
        else:
            return False
        
    
