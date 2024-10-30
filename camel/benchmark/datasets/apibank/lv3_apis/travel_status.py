from apis.api import API
class TravelStatus(API):
    description = "API for retrieving the current travel status of each member."
    input_parameters = {
        'member_name': {'type': 'str', 'description': 'Name of the member.'},
    }
    output_parameters = {
        'status': {'type': 'str', 'description': 'Travel status'},
    }

    def __init__(self):
        self.database = {
            'John': 'Traveling',
            'Mary': 'Working from home',
            'Peter': 'Working from office',
            'Tom': 'Traveling',
            'Jerry': 'Working from home',
            'Jack': 'Working from office',
            'Rose': 'Working from office',
            'Bob': 'Traveling',
            'Alice': 'Working from home',
            'Mike': 'Working from office',
            'Jane': 'Working from office',
        }


    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): The response from the API call.
        - groundtruth (dict): The groundtruth response.

        Returns:
        - is_correct (bool): Whether the response is correct.
        """
        assert response['api_name'] == groundtruth['api_name'], "The API name is not correct."
        return response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception'] and response['input'] == groundtruth['input']


    def call(self, member_name: str) -> dict:
        input_parameters = {'member_name': member_name}
        try:
            status = self.get_travel_status(member_name)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': status,
                    'exception': None}


    def get_travel_status(self, member_name):
        return self.database[member_name]