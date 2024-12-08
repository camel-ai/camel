import requests
from apis.api import API

class GetWeatherForCoordinates(API):
    description = "Retrieves current weather information based on the provided coordinates."
    input_parameters = {
        'latitude': {'type': 'float', 'description': 'Latitude of the location.'},
        'longitude': {'type': 'float', 'description': 'Longitude of the location.'}
    }
    output_parameters = {
        'temperature': {'type': 'float', 'description': 'Current temperature in Celsius.'},
        'humidity': {'type': 'float', 'description': 'Current humidity level.'},
        'description': {'type': 'str', 'description': 'Weather description.'}
    }

    def __init__(self):
        self.coordinates_to_weather = [
            ((40.7128, 74.0060), {
                'temperature': 10,
                'humidity': 0.5,
                'description': 'Clear'
            }),
            ((37.7749, 122.4194), {
                'temperature': 20,
                'humidity': 0.8,
                'description': 'Cloudy'
            }),
            ((51.5074, 0.1278), {
                'temperature': 5,
                'humidity': 0.9,
                'description': 'Rainy'
            }),
            ((48.8566, 2.3522), {
                'temperature': 15,
                'humidity': 0.7,
                'description': 'Sunny'
            }),
            ((35.6762, 139.6503), {
                'temperature': 25,
                'humidity': 0.6,
                'description': 'Rainy'
            }),
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
        return response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception'] and response['input'] == groundtruth['input']

    def call(self, latitude: float, longitude: float) -> dict:
        input_parameters = {
            'latitude': latitude,
            'longitude': longitude
        }
        try:
            response = self.fetch_weather(latitude, longitude)
            output_parameters = {
                'temperature': response['temperature'],
                'humidity': response['humidity'],
                'description': response['description']
            }
        except requests.exceptions.RequestException as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None, 'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': output_parameters, 'exception': None}

    def fetch_weather(self, latitude, longitude):
        for coordinates, weather in self.coordinates_to_weather:
            if coordinates == (latitude, longitude):
                return weather