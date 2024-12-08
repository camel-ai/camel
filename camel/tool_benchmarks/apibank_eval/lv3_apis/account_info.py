from apis.api import API
class AccountInfo(API):
    description = "API for retrieving and updating user account information."
    input_parameters = {
        'username': {'type': 'str', 'description': 'Name of the user.'},
        'password': {'type': 'str', 'description': 'Password of the user.'},
    }
    output_parameters = {
        'status': {'type': 'str', 'description': 'success or failed'},
        'account_info': {'type': 'dict', 'description': 'User account information'}
    }

    def __init__(self):
        self.database = [
            (('John', '123456'), {'email': 'john@example.com', 'phone': '1234567890'}),
            (('Mary', 'abcdef'), {'email': 'mary@example.com', 'phone': '0987654321'}),
            (('Peter', 'qwerty'), {'email': 'peter@example.com', 'phone': '1231231234'}),
            (('Tom', 'asdfgh'), {'email': 'tom@example.com', 'phone': '4564564567'}),
            (('Jerry', 'zxcvbn'), {'email': 'jerry@example.com', 'phone': '7897897890'}),
        ]

    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response.

        Returns:
        - is_correct (bool): whether the response is correct.
        """
        assert response['api_name'] == groundtruth['api_name'], "The API name is not correct."
        return response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception'] and response['input'] == groundtruth['input']

    def call(self, username: str, password: str) -> dict:
        input_parameters = {
            'username': username,
            'password': password
        }
        try:
            account_info = self.retrieve_account_info(username, password)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': account_info, 'exception': None}
    
    def retrieve_account_info(self, username, password):
        for (user, pwd), account_info in self.database:
            if user == username and pwd == password:
                return account_info
        raise Exception('User not found.')