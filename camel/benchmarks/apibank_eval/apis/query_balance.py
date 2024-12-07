from apis.api import API

class QueryBalance(API):
    description = 'This API queries the balance of a given user.'

    input_parameters = {
        "token": {'type': 'str', 'description': 'The token of the user.'},
    }
    output_parameters = {
        "balance": {'type': 'float', 'description': 'The balance of the user.'},
    }
    database_name = 'Bank'


    def __init__(self, init_database=None, token_checker=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}
        assert token_checker != None
        self.token_checker = token_checker
    
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
            balance = self.query_balance(token)
        except Exception as e:
            exception = str(e)
            return {
                'api_name': self.__class__.__name__,
                'input': input_parameters,
                'output': None,
                'exception': exception,
            }
        else:
            return {
                'api_name': self.__class__.__name__,
                'input': input_parameters,
                'output': balance,
                'exception': None,
            }

    def query_balance(self, token: str) -> float:
        """
        Queries the balance of a given user.

        Parameters:
        - token (str): the token of the user.

        Returns:
        - balance (float): the balance of the user.
        """

        #check if the token is correct
        try:
            # Here token_checker should be used
            token.strip()
            username = self.token_checker.check_token(token)
        except Exception as e:
            raise Exception('The token is incorrect.')
        
        """
        database = {
            'username1': {
                'balance': 100.0,
                ...
            },
            'username2': {
                'balance': 200.0,
                ...
            },
            'username3': {
                'balance': 300.0,
                ...
            },
        }
        """
        #check if the username has an account
        if username not in self.database:
            raise Exception('The user does not have an account.')
        
        return self.database[username]['balance']
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        response_token = response['input']['token'].strip()
        groundtruth_token = groundtruth['input']['token'].strip()

        response_balance = response['output']
        groundtruth_balance = groundtruth['output']

        if response_token == groundtruth_token and response_balance == groundtruth_balance and response['exception'] == groundtruth['exception']:
            return True
        else:
            return False