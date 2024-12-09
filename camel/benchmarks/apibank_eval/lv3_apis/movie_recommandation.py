from apis.api import API
class MovieRecommendations(API):
    description = "The API for retrieving recommended movies based on user preferences and filtering watched movies."
    input_parameters = {
        'preferences': {'type': 'list', 'description': "User's movie preferences."},
    }
    output_parameters = {
        'recommended_movies': {'type': 'list', 'description': 'List of recommended movies.'}
    }

    def __init__(self):
        self.database = {
            'Action': ['The Dark Knight', 'The Matrix', 'The Lord of the Rings'],
            'Comedy': ['The Hangover', 'Knives Out', 'Deadpool'],
            'Drama': ['The Shawshank Redemption', 'Forrest Gump', 'Joker'],
            'Romance': ['Titanic', 'La La Land', 'The Notebook'],
            'Thriller': ['Inception', 'Parasite', 'Get Out'],
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


    def call(self, preferences: list) -> dict:
        input_parameters = {
            'preferences': preferences,
        }
        try:
            recommended_movies = self.get_recommendations(preferences)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': {'recommended_movies': recommended_movies},
                    'exception': None}


    def get_recommendations(self, preferences: list) -> list:
        recommended_movies = []        

        for preference in preferences:
            movies = self.database[preference]
            recommended_movies.extend(movies)

        return recommended_movies
