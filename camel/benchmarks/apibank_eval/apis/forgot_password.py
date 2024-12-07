from apis.api import API
import json
import random

class ForgotPassword(API):

    description = 'Sends an email to the user with a link to reset the password. Need call twice, first with \'Forgot Password\' status to get the verification code, then call again with \'Verification Code\' status to change the password. Must pass the name of the parameters when calling the API, like ForgotPassword(status=\'Forgot Password\', username=\'username\').'
    input_parameters = {
        "status": {"type": "str", "description": "\'Forgot Password\' for first call, after get the verification code, call again with \'Verification Code\' to change the password."},
        "username": {"type": "str", "description": "The username of the user. Only needed for the first call."},
        "email": {"type": "str", "description": "The email of the user. Only needed for the first call."},
        "verification_code": {"type": "int", "description": "The verification code sent to the user. Only needed for the second call."},
        "new_password": {"type": "str", "description": "The new password of the user. Only needed for the second call."},
    }
    output_parameters = {
        "status": {"type": "str", "description": "success or failed"},
    }
    database_name = "Account"

    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

        self.verification_code = None
        self.username = None

    def forgot_password(self, status: str, **kwargs) -> str:
        """
        Sends an email to the user with a link to reset the password. Need call twice, first with 'Forgot Password' status to get the verification code, then call again with 'Verification Code' status to change the password.

        Parameters:
        - status (str): 'Forgot Password' for first call, after get the verification code, call again with 'Verification Code' to change the password.
        - username (str): The username of the user. Only needed for the first call.
        - email (str): The email of the user. Only needed for the first call.
        - new_password (str): The new password of the user. Only needed for the second call.

        Returns:
        - status (str): success or failed
        """
        if status == "Forgot Password":
            if "username" not in kwargs or "email" not in kwargs:
                raise Exception("The username and email are required for the first call.")
            username = kwargs["username"]
            email = kwargs["email"]
            if username not in self.database:
                raise Exception("The username does not exist.")
            if self.database[username]["email"] != email:
                raise Exception("The email is incorrect.")
            self.verification_code = 970420 # random.randint(100000, 999999)
            self.username = username
            return self.verification_code
        elif status == "Verification Code":
            if not self.verification_code:
                raise Exception("You need to call the API with status \'Forgot Password\' at first.")
            if "new_password" not in kwargs or "verification_code" not in kwargs:
                raise Exception("The new password and verification code are required for the second call.")
            new_password = kwargs["new_password"]
            verification_code = kwargs["verification_code"]
            if self.verification_code == verification_code:
                self.database[self.username]["password"] = new_password
                return "success"
            else:
                raise Exception("The verification code is incorrect.")
        else:
            raise Exception("The status is only \'Forgot Password\' or \'Verification Code\'.")
        
    def call(self, status: str, **kwargs) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - status (str): 'Forgot Password' for first call, after get the verification code, call again with 'Verification Code' to change the password.
        - username (str): The username of the user. Only needed for the first call.
        - email (str): The email of the user. Only needed for the first call.
        - new_password (str): The new password of the user. Only needed for the second call.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            "status": status,
            **kwargs,
        }
        try:
            output = self.forgot_password(status, **kwargs)
        except Exception as e:
            exception = str(e)
            return {
                "input": input_parameters,
                "output": None,
                "exception": exception,
            }
        return {
            "input": input_parameters,
            "output": output,
            "exception": None,
        }
        
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response from the API call.

        Returns:
        - correctness (bool): True if the response is correct, False otherwise.
        """
        if response['input'] == groundtruth['input'] and response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception']:
            return True
        else:
            return False

