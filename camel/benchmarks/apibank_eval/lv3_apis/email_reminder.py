import datetime
from apis.api import API

class EmailReminder(API):
    description = "This API sends an email reminder to the user with the meeting details."
    input_parameters = {
        'content': {'type': 'str', 'description': 'The content of the email.'},
        'time': {'type': 'str', 'description': 'The time for the meeting. Format: %Y-%m-%d %H:%M:%S'},
        'location': {'type': 'str', 'description': 'The location of the meeting.'},
        'recipient': {'type': 'str', 'description': 'The email address of the recipient.'},
    }
    output_parameters = {
        'status': {'type': 'str', 'description': 'success or failed'}
    }

    def __init__(self):
        pass

    def call(self, content: str, time: str, location: str, recipient: str) -> dict:
        input_parameters = {
            'content': content,
            'time': time,
            'location': location,
            'recipient': recipient
        }
        try:
            self.send_email(content, time, location, recipient)
            status = 'success'
        except Exception as e:
            status = 'failed'
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None, 'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': status, 'exception': None}

    def send_email(self, content: str, time: str, location: str, recipient: str):
        # Validate the input parameters
        datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S')

        if content.strip() == "":
            raise Exception('Content should not be empty')

        # Send the email to the recipient
        # email_subject = f"Meeting Reminder: {content}"
        # email_body = f"Meeting Details:\n\nContent: {content}\nTime: {time}\nLocation: {location}"
        # self.email_sender.send_email(token, recipient, email_subject, email_body)
        return 'success'
    
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
        response['input'].pop('content')
        groundtruth['input'].pop('content')
        return response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception'] and response['input'] == groundtruth['input']