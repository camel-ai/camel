from apis.api import API

class UserWatchedMovies(API):
    description = "API for retrieving a user's watched movie list."
    input_parameters = {
        'user_name': {'type': 'str', 'description': 'Name of the user.'},
    }
    output_parameters = {
        'watched_movies': {'type': 'list', 'description': 'List of watched movies.'},
    }

    def __init__(self):
        self.database = {
            'John': ['The Matrix', 'The Lord of the Rings', 'The Dark Knight'],
            'Mary': ['The Lord of the Rings', 'The Dark Knight', 'The Matrix'],
            'Peter': ['The Matrix', 'The Lord of the Rings', 'The Dark Knight'],
            'Tom': ['The Lord of the Rings', 'The Dark Knight', 'The Matrix'],
            'Jerry': ['The Matrix', 'The Lord of the Rings', 'The Dark Knight'],
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
            watched_movies = self.retrieve_watched_movies(user_name)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': watched_movies,
                    'exception': None}

    def retrieve_watched_movies(self, user_name):
        if user_name not in self.database:
            raise Exception('User not found.')

        return self.database[user_name]

