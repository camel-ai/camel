from apis.api import API

class PersonalInfoUpdate(API):
    description = "The API for updating a user's personal information and address."
    input_parameters = {
        'username': {'type': 'str', 'description': 'Name of the user.'},
        'password': {'type': 'str', 'description': 'Password of the user.'},
        'address': {'type': 'str', 'description': 'Updated address information.'},
    }
    output_parameters = {
        'status': {'type': 'str', 'description': 'Success or failure'},
    }
    

    def __init__(self):
        self.database = [
            (('John', '123456'), {'email': 'john@example.com', 'phone': '1234567890'}),
            (('Mary', 'abcdef'), {'email': 'mary@example.com', 'phone': '0987654321'}),
            (('Peter', 'qwerty'), {'email': 'peter@example.com', 'phone': '1231231234'}),
            (('Tom', 'asdfgh'), {'email': 'tom@example.com', 'phone': '4564564567'}),
            (('Jerry', 'zxcvbn'), {'email': 'jerry@example.com', 'phone': '7897897890'}),
        ]


    def check_api_call_correctness(self, response, groundtruth):
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response.

        Returns:
        - is_correct (bool): whether the response is correct.
        """
        assert response['api_name'] == groundtruth['api_name'], "The API name is not correct."
        return response['input'] == groundtruth['input'] and response['output'] == groundtruth['output']


    def call(self, username: str, password: str, address: dict) -> dict:
        input_parameters = {
            'username': username,
            'password': password,
            'address': address
        }
        try:
            status = self.update_personal_info(username, password, address)
            output_parameters = {
                'status': status
            }
        except Exception as e:
            exception = str(e)
            return {
                'api_name': self.__class__.__name__,
                'input': input_parameters,
                'output': None,
                'exception': exception
            }
        else:
            return {
                'api_name': self.__class__.__name__,
                'input': input_parameters,
                'output': output_parameters,
                'exception': None
            }


    def update_personal_info(self, username, password, address):
        for (user, pwd), user_account in self.database:
            if user == username and pwd == password:
                user_account['address'] = address
                return 'success'
        raise Exception('User not found.')

