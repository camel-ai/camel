from apis.api import API
# from api import API
import re

class SendEmail(API):
    description = 'This API for sending email, given the receiver, subject and content.'
    input_parameters = {
        "receiver": {'type': 'str', 'description': 'The receiver address of the email.'},
        "subject": {'type': 'str', 'description': 'The subject address of the email.'},
        "content": {'type': 'str', 'description': 'The content of the email.'},
    }
    output_parameters = {
        "status": {'type': 'str', 'description': 'The status of the email.'},
    }

    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def call(self, receiver: str, subject: str, content: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - sender (str): the sender of the email.
        - receiver (str): the receiver of the email.
        - subject (str): the subject of the email.
        - content (str): the content of the email.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'receiver': receiver,
            'subject': subject,
            'content': content,
        }
        try:
            status = self.send_email(receiver, subject, content)
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
            'output': status,
            'exception': None,
        }
    
    def send_email(self, receiver: str, subject: str, content: str) -> str:
        """
        Sends an email.

        Parameters:
        - receiver (str): the receiver of the email.
        - subject (str): the subject of the email.
        - content (str): the content of the email.

        Returns:
        - status (str): the status of the email.
        """
        receiver = receiver.strip()
        subject = subject.strip()
        content = content.strip()

        def check_email(email: str) -> bool:
            """
            Checks if the email is valid.

            Parameters:
            - email (str): the email to be checked.

            Returns:
            - is_valid (bool): whether the email is valid.
            """
            # email regex
            regex = re.compile(r"^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$")
            if regex.match(email):
                return True
            else:
                return False

        if check_email(receiver):
            pass
        else:
            raise Exception('Email address of the receiver is invalid.')

        if subject == '':
            raise Exception('Subject cannot be empty.')
        
        if content == '':
            raise Exception('Content cannot be empty.')

        return "success"
            
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response from the API call.

        Returns:
        - correctness (bool): True if the response is correct, False otherwise.
        """
        response_receiver = response['input']['receiver'].strip().lower()
        groundtruth_receiver = groundtruth['input']['receiver'].strip().lower()
        response_subject = response['input']['subject'].strip()
        groundtruth_subject = groundtruth['input']['subject'].strip()
        response_content = response['input']['content'].strip()
        groundtruth_content = groundtruth['input']['content'].strip()
        if response_receiver == groundtruth_receiver and response_subject == groundtruth_subject and response_content == groundtruth_content and response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception']:
            return True
        else:
            return False
        
