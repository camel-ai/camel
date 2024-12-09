from apis.api import API
class NearbyRestaurants(API):
    description = "Retrieves nearby restaurants based on the provided coordinates and search parameters."
    input_parameters = {
        'latitude': {'type': 'float', 'description': 'Latitude of the location.'},
        'longitude': {'type': 'float', 'description': 'Longitude of the location.'},
        'distance': {'type': 'int', 'description': 'The distance in meters from the location to search for restaurants.'},
    }
    output_parameters = {
        'restaurants': {'type': 'list', 'description': 'A list of nearby restaurants.'},
    }

    def __init__(self):
        self.restaurants = [
            {'coordinates': (40.7128, 74.0060), 'name': 'Restaurant A'},
            {'coordinates': (37.7749, 122.4194), 'name': 'Restaurant B'},
            {'coordinates': (40.7128, 74.0060), 'name': 'Restaurant C'},
            {'coordinates': (37.7749, 122.4194), 'name': 'Restaurant D'},
        ]

    def get_nearby_restaurants(self, latitude: float, longitude: float, distance: int) -> list:
        """
        Retrieves nearby restaurants based on the provided coordinates and search parameters.

        Parameters:
        - latitude (float): latitude of the location.
        - longitude (float): longitude of the location.
        - distance (int): the distance in meters from the location to search for restaurants.

        Returns:
        - restaurants (list): a list of nearby restaurants.
        """
        return self.restaurants

    def check_api_call_correctness(self, response, groundtruth):
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response.

        Returns:
        - is_correct (bool): whether the response is correct.
        """
        assert response['api_name'] == groundtruth['api_name'], "The API name is not correct."
        return response['input'] == groundtruth['input']

    def call(self, latitude: float, longitude: float, distance: int) -> dict:
        input_parameters = {
            'latitude': latitude,
            'longitude': longitude,
            'distance': distance
        }
        try:
            restaurants = self.get_nearby_restaurants(latitude, longitude, distance)
            output_parameters = {
                'restaurants': restaurants
            }
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None, 'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': output_parameters, 'exception': None}

