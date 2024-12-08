from apis.api import API

class Geocoding(API):
    description = "The API for converting an address or place name to geographical coordinates."
    input_parameters = {
        'address': {'type': 'str', 'description': 'The address or place name to be converted.'},
    }
    output_parameters = {
        'latitude': {'type': 'float', 'description': 'The latitude of the location.'},
        'longitude': {'type': 'float', 'description': 'The longitude of the location.'},
    }

    def __init__(self):
        self.address_to_coordinates = {
            'New York City': (40.7128, 74.0060),
            'San Francisco': (37.7749, 122.4194),
            'London': (51.5074, 0.1278),
            'Paris': (48.8566, 2.3522),
            'Tokyo': (35.6762, 139.6503),
        }

    def call(self, address: str) -> dict:
        input_parameters = {
            'address': address,
        }
        try:
            latitude, longitude = self.convert_address_to_coordinates(address)
            output_parameters = {
                'latitude': latitude,
                'longitude': longitude,
            }
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None, 'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': output_parameters, 'exception': None}

    def convert_address_to_coordinates(self, address: str) -> tuple:
        return self.address_to_coordinates[address]
    
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