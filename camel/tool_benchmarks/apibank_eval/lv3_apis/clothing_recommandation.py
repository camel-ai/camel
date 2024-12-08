from apis.api import API
class ClothingRecommendation(API):
    description = "API for providing clothing recommendations based on weather conditions."
    input_parameters = {
        'temperature': {'type': 'float', 'description': 'Temperature in Celsius.'},
        'humidity': {'type': 'float', 'description': 'Relative humidity in percentage.'},
        'weather_conditions': {'type': 'str', 'description': 'Description of weather conditions.'},
    }
    output_parameters = {
        'clothing_options': {'type': 'list', 'description': 'List of recommended clothing options.'},
    }

    def call(self, temperature: float, humidity: float, weather_conditions: str) -> dict:
        input_parameters = {
            'temperature': temperature,
            'humidity': humidity,
            'weather_conditions': weather_conditions,
        }
        try:
            clothing_options = self.get_clothing_recommendation(temperature, humidity, weather_conditions)
            return {
                'api_name': self.__class__.__name__,
                'input': input_parameters,
                'output': {'clothing_options': clothing_options},
                'exception': None
            }
        except Exception as e:
            exception = str(e)
            return {
                'api_name': self.__class__.__name__,
                'input': input_parameters,
                'output': None,
                'exception': exception
            }

    def get_clothing_recommendation(self, temperature: float, humidity: float,
                                    weather_conditions: str) -> list:
        # Clothing recommendation logic based on weather conditions
        clothing_options = []

        if temperature < 10:
            clothing_options.append('Warm coat')
            clothing_options.append('Hat')
            clothing_options.append('Gloves')

        if temperature >= 10 and temperature < 20:
            clothing_options.append('Light jacket')
            clothing_options.append('Long-sleeved shirt')

        if temperature >= 20 and temperature < 30:
            clothing_options.append('T-shirt')
            clothing_options.append('Shorts')

        if temperature >= 30:
            clothing_options.append('Sun hat')
            clothing_options.append('Sunglasses')
            clothing_options.append('Loose-fitting clothes')

        if humidity > 70:
            clothing_options.append('Umbrella')
            clothing_options.append('Waterproof shoes')


        if 'rain' in weather_conditions.lower():
            clothing_options.append('Raincoat')

        return clothing_options

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