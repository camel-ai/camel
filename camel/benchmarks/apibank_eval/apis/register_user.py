from apis.api import API
import string
import random
import json

class RegisterUser(API):

    description = 'The API for registering a account, given the username, password and email.'
    input_parameters = {
        'username': {'type': 'str', 'description': 'The username of the user.'},
        'password': {'type': 'str', 'description': 'The password of the user.'},
        'email': {'type': 'str', 'description': 'The email of the user.'},
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

    def register_user(self, username: str, password: str, email: str) -> str:
        """
        Registers a user.
        
        Parameters:
        - username (str): the username of the user.
        - password (str): the password of the user.
        - email (str): the email of the user.
        
        Returns:
        - token (str): the token of the user.
        """
        if username in self.database:
            raise Exception('The username already exists.')
        token = self.generate_token()
        self.database[username] = {
            'password': password,
            'token': token,
            'email': email,
        }
        return token
    
    def generate_token(self, length: int = 18) -> str:
        """
        Generates a token.

        Parameters:
        - length (int): the length of the token.

        Returns:
        - token (str): the generated token.
        """
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length)).lower()
    
    def call(self, username: str, password: str, email: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - username (str): the username of the user.
        - password (str): the password of the user.
        - email (str): the email of the user.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'username': username,
            'password': password,
            'email': email,
        }
        try:
            token = self.register_user(username, password, email)
            output_parameters = {
                'token': token,
            }
        except Exception as e:
            exception = str(e)
            return {
                'input': input_parameters,
                'output': None,
                'exception': exception,
            }
        return {
            'input': input_parameters,
            'output': output_parameters,
            'exception': None,
        }
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks the correctness of the API call.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth of the API call.

        Returns:
        - is_correct (bool): whether the API call is correct.
        """
        if groundtruth['output'] == None and response['output'] != None:
            return False

        if response['input'] == groundtruth['input'] and response['exception'] == groundtruth['exception']:
            return True
        else:
            return False
        
    def dump_database(self, filename: str) -> None:
        """
        Dumps the database to a file.

        Parameters:
        - filename (str): the filename of the database file.
        """
        with open(filename, 'w') as f:
            json.dump(self.database, f, ensure_ascii=False)


