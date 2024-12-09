from apis.api import API

class UserMoviePreferences(API):
    description = "API for retrieving user preferences for movie recommendations."
    input_parameters = {
        'user_name': {'type': 'str', 'description': 'Name of the user.'},
    }
    output_parameters = {
        'preferences': {'type': 'list', 'description': 'List of movie preferences.'},
    }

    def __init__(self):
        self.database = {
            'John': ['Action', 'Comedy', 'Drama'],
            'Mary': ['Comedy', 'Drama', 'Romance'],
            'Peter': ['Action', 'Drama', 'Thriller'],
            'Tom': ['Action', 'Comedy', 'Drama'],
            'Jerry': ['Comedy', 'Drama', 'Romance'],
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

    def call(self, user_name: str) -> dict:
        input_parameters = {
            'user_name': user_name
        }
        try:
            preferences = self.retrieve_preferences(user_name)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None, 'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': {'preferences': preferences}, 'exception': None}

    def retrieve_preferences(self, user_name):
        return self.database[user_name]
