import datetime
from apis.api import API

class QueryMeeting(API):
    description = "The API for retrieving the meeting details from the user's calendar."
    input_parameters = {
        'user_name': {'type': 'str', 'description': 'Name of the user.'},
    }
    output_parameters = {
        'meetings': {'type': 'list', 'description': 'List of meetings.'},
    }

    def __init__(self):
        self.database = {
            'John': [
                {
                    'meeting_id': 1,
                    'meeting_name': 'Meeting with the client',
                    'meeting_time': datetime.datetime(2021, 1, 1, 10, 0, 0).strftime('%Y-%m-%d %H:%M:%S'),
                    'meeting_location': 'Room 1',
                    'meeting_attendees': ['John', 'Mary', 'Peter'],
                },
                {
                    'meeting_id': 2,
                    'meeting_name': 'Meeting about the new project',
                    'meeting_time': datetime.datetime(2021, 1, 2, 10, 0, 0).strftime('%Y-%m-%d %H:%M:%S'),
                    'meeting_location': 'Room 2',
                    'meeting_attendees': ['John', 'Mary', 'Peter'],
                },
            ],
            'Mary': [
                {
                    'meeting_id': 1,
                    'meeting_name': 'Meeting with the client',
                    'meeting_time': datetime.datetime(2021, 1, 1, 10, 0, 0).strftime('%Y-%m-%d %H:%M:%S'),
                    'meeting_location': 'Room 1',
                    'meeting_attendees': ['John', 'Mary', 'Peter'],
                },
                {
                    'meeting_id': 2,
                    'meeting_name': 'Meeting about the new project',
                    'meeting_time': datetime.datetime(2021, 1, 2, 10, 0, 0).strftime('%Y-%m-%d %H:%M:%S'),
                    'meeting_location': 'Room 2',
                    'meeting_attendees': ['John', 'Mary', 'Peter'],
                },
            ],
            'Peter': [
                {
                    'meeting_id': 1,
                    'meeting_name': 'Meeting with the client',
                    'meeting_time': datetime.datetime(2021, 1, 1, 10, 0, 0).strftime('%Y-%m-%d %H:%M:%S'),
                    'meeting_location': 'Room 1',
                    'meeting_attendees': ['John', 'Mary', 'Peter'],
                },
                {
                    'meeting_id': 2,
                    'meeting_name': 'Meeting about the new project',
                    'meeting_time': datetime.datetime(2021, 1, 2, 10, 0, 0).strftime('%Y-%m-%d %H:%M:%S'),
                    'meeting_location': 'Room 2',
                    'meeting_attendees': ['John', 'Mary', 'Peter'],
                },
            ],
            'Tom': [
                {
                    'meeting_id': 1,
                    'meeting_name': 'Meeting',
                    'meeting_time': datetime.datetime(2021, 1, 1, 10, 0, 0).strftime('%Y-%m-%d %H:%M:%S'),
                    'meeting_location': 'Room 1',
                    'meeting_attendees': ['Tom', 'Jerry'],
                },
            ],
            'Jerry': [
                {
                    'meeting_id': 1,
                    'meeting_name': 'Meeting',
                    'meeting_time': datetime.datetime(2021, 1, 1, 10, 0, 0).strftime('%Y-%m-%d %H:%M:%S'),
                    'meeting_location': 'Room 1',
                    'meeting_attendees': ['Tom', 'Jerry'],
                },
            ],
        }
                 

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

    def call(self, user_name):
        input_parameters = {
            'user_name': user_name,
        }
        try:
            meetings = self.retrieve_user_meetings(user_name)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None, 'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': {'meetings': meetings}, 'exception': None}
        
    def retrieve_user_meetings(self, user_name):
        return self.database[user_name]